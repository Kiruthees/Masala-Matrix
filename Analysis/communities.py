import numpy as np, pandas as pd, networkx as nx, matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from networkx.algorithms import bipartite
from networkx.algorithms.community import louvain_communities

NODES, EDGES = "nodes_9.0.csv", "edges_6.0.csv"
OUT = "communities_and_cuisines.png"
MIN_RECIPES = 60          # cuisines shown in heatmap
N_COMM = 4                # communities to keep
SEED = 42
N_LABELS = 22             
PALETTE = ["#C0444B", "#E2A62E", "#4A6FAF", "#55A868"]  # red, gold, blue, green

nodes, edges = pd.read_csv(NODES), pd.read_csv(EDGES)
rec = nodes[nodes.Type == "Recipe"].copy()
ing = nodes[nodes.Type != "Recipe"]
rec["Cuisine"] = rec.Cuisine.str.replace(" Recipes", "", regex=False)

B = nx.Graph()
B.add_nodes_from(rec.Id, bipartite=0)
B.add_nodes_from(ing.Id, bipartite=1)
B.add_edges_from(edges[["Source", "Target"]].itertuples(index=False, name=None))
n_use = {i: B.degree(i) for i in ing.Id}              # recipes using each ingredient

I0 = bipartite.weighted_projected_graph(B, set(ing.Id))
I = nx.Graph()                                   # rebuild in sorted order -> reproducible Louvain
I.add_nodes_from(sorted(I0))
I.add_weighted_edges_from(sorted((min(u, v), max(u, v), d["weight"]) for u, v, d in I0.edges(data=True)))

# --------------------------------------- Louvain -> exactly N_COMM communities
def get_communities(G, n_comm=N_COMM, min_size=60):
    """Scan resolution/seed until Louvain gives n_comm sizeable communities."""
    for res in np.arange(0.8, 2.01, 0.05):
        for s in range(SEED, SEED + 10):
            C = [c for c in louvain_communities(G, weight="weight", resolution=res, seed=s)
                 if len(c) >= min_size]
            if len(C) == n_comm:
                return sorted(C, key=len, reverse=True)
    C = sorted(louvain_communities(G, weight="weight", seed=SEED), key=len, reverse=True)
    return C[:n_comm]

C = get_communities(I)
comm = {x: k for k, c in enumerate(C) for x in c}
for k, c in enumerate(C):
    print(k, len(c), sorted(c, key=n_use.get, reverse=True)[:10])

# ----- name communities: edit this mapping after looking at the printout above
NAMES = ["North Indian gravy base", "Sweets, dairy & baking",
         "South Indian tempering & coconut", "Vegetables & continental"]
SIGNATURE = [["onion", "tomato", "garam masala", "ginger", "garlic"],
             ["ghee", "sugar", "milk", "cardamom", "cashew nuts"],
             ["curry leaves", "mustard seeds", "asafoetida", "coconut", "urad dal"],
             ["potato", "carrot", "capsicum", "cabbage", "cheese"]]
score = np.array([[sum(i in c for i in sig) for sig in SIGNATURE] for c in C])
order = [None] * N_COMM; used = set()
for k in np.argsort(-score.max(1)):                    # greedy match community -> name
    j = max((j for j in range(N_COMM) if j not in used), key=lambda j: score[k, j])
    order[k] = j; used.add(j)
cname = {k: NAMES[order[k]] for k in range(N_COMM)}
ccolor = {k: PALETTE[order[k]] for k in range(N_COMM)}

# ----------------------------------------------- enrichment (log2 vs overall)
ed = edges[edges.Target.isin(comm)].merge(rec[["Id", "Cuisine"]], left_on="Source", right_on="Id")
ed["c"] = ed.Target.map(comm)
K = range(N_COMM)
overall = ed.c.value_counts(normalize=True).reindex(K).fillna(0)
rows = {}
for cu, g in ed.groupby("Cuisine"):
    nr = g.Source.nunique()
    if nr >= MIN_RECIPES:
        share = g.c.value_counts(normalize=True).reindex(K).fillna(0)
        rows[f"{cu} (n={nr})"] = np.log2((share + 1e-9) / (overall + 1e-9))
H = pd.DataFrame(rows).T
H.columns = [cname[k] for k in K]
H = H[NAMES]                                            # fixed column order
# order cuisines by South-Indian enrichment minus North-Indian enrichment
H = H.loc[(H[NAMES[2]] - H[NAMES[0]]).sort_values(ascending=False).index]

# ------------------------------------------------------------------ figure
fig = plt.figure(figsize=(24, 10.5), dpi=200)
ax = fig.add_axes([0.01, 0.02, 0.48, 0.90])
axh = fig.add_axes([0.585, 0.08, 0.355, 0.78])
cax = fig.add_axes([0.955, 0.08, 0.008, 0.78])

# ---- left: network
# layout on a pruned copy (weak links removed) so structure is visible; draw the same graph
Ip = nx.Graph([(u, v, d) for u, v, d in I.edges(data=True) if d["weight"] >= 2])
Ip.add_nodes_from(I)
for u, v, d in I.edges(data=True):
    d["lw"] = np.log1p(d["weight"])               # damp heavy edges so the core spreads out
pos = nx.spring_layout(I, weight="lw", k=0.9, iterations=300, seed=SEED)
sizes = np.array([5 + 1.1 * n_use[v] ** 0.95 for v in I])
ax.set_axis_off()
nx.draw_networkx_edges(Ip, pos, ax=ax, width=0.3, alpha=0.12, edge_color="#444444")
nx.draw_networkx_nodes(I, pos, ax=ax, node_size=sizes, alpha=0.85, linewidths=0,
                       node_color=[ccolor[comm[v]] if v in comm else "#BBBBBB" for v in I])
top = sorted(I, key=n_use.get, reverse=True)[:N_LABELS]
for v in top:
    ax.text(*pos[v], v, fontsize=11, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.7))
ax.set_title("Ingredient network: Louvain communities (node size = recipes using it)",
             fontsize=17, fontweight="bold", loc="left")
for j, nm in enumerate(NAMES):
    ax.scatter([], [], s=140, color=PALETTE[j], label=nm)
ax.legend(loc="lower left", frameon=False, fontsize=15, handletextpad=0.6, labelspacing=0.7)

# ---- right: heatmap
vmax = 0.8   # colour scale clipped at +/-0.8 (values beyond saturate)
im = axh.imshow(H.values, cmap="RdBu_r", norm=Normalize(-vmax, vmax), aspect="auto")
axh.set_yticks(range(len(H))); axh.set_yticklabels(H.index, fontsize=13)
axh.set_xticks(range(N_COMM))
axh.set_xticklabels([n.replace(" & ", " &\n").replace(", ", ",\n") if len(n) > 20 else n
                     for n in NAMES], fontsize=12)
axh.xaxis.set_ticks_position("bottom")
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        axh.text(j, i, f"{H.values[i, j]:+.2f}", ha="center", va="center", fontsize=12)
for s in ("top", "right"): axh.spines[s].set_visible(False)
axh.set_title("Which ingredient communities each cuisine over-uses\n(log2 enrichment vs. overall)",
              fontsize=19, fontweight="bold")
fig.colorbar(im, cax=cax, ticks=np.arange(-0.8, 0.81, 0.2))
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print("saved", OUT)