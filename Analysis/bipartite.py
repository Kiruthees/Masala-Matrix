# This code is a authored by Raghav Y
# Makes the firest iteration of the bipartite network
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET

df = pd.read_csv("ingredient_dish_edges.csv")

B = nx.Graph()
# Node creation
for i, row in df[["Dish_ID", "Dish", "Region"]].drop_duplicates("Dish_ID").iterrows():
    B.add_node(
        row["Dish_ID"],
        bipartite=0,
        node_type="dish",
        name=str(row["Dish"]),
        region=str(row["Region"]),
    )
ingredients = df["Ingredient"].dropna().unique()

for ingredient in ingredients:
    ingredient = str(ingredient).strip()
    ingredient_id = f"ING::{ingredient.lower()}"

    B.add_node(
        ingredient_id,
        bipartite=1,
        node_type="ingredient",
        name=ingredient,
    )

for i, row in df.dropna(subset=["Ingredient"]).iterrows():
    ingredient = str(row["Ingredient"]).strip()
    ingredient_node = f"ING::{ingredient.lower()}"

    B.add_edge(
        row["Dish_ID"],
        ingredient_node,
        quantity=str(row["Quantity"]),
    )

print("Number of nodes:", B.number_of_nodes())
print("Number of edges:", B.number_of_edges())
print("Is bipartite:", nx.is_bipartite(B))

# Coordinates since gephi does not have bipartite sorting as far as I know
dish_nodes = [
    n for n, d in B.nodes(data=True)
    if d["bipartite"] == 0
]

ingredient_nodes = [
    n for n, d in B.nodes(data=True)
    if d["bipartite"] == 1
]

# Layout given for now lambda is anonymous function use proper function if needed!
dish_nodes.sort(key=lambda n: str(B.nodes[n]["name"]).lower())
ingredient_nodes.sort(key=lambda n: str(B.nodes[n]["name"]).lower())

# Vertical spacing params for making it look like bipartite
dish_spacing = 100
ingredient_spacing = 100

for i, node in enumerate(dish_nodes):
    B.nodes[node]["x"] = -500.0
    B.nodes[node]["y"] = (
        (len(dish_nodes) - 1) / 2 - i
    ) * dish_spacing

for i, node in enumerate(ingredient_nodes):
    B.nodes[node]["x"] = 500.0
    B.nodes[node]["y"] = (
        (len(ingredient_nodes) - 1) / 2 - i
    ) * ingredient_spacing

# Open gexf in gephi later

import xml.etree.ElementTree as ET

# Make the visible labels the actual dish/ingredient names
for node, data in B.nodes(data=True):
    data["label"] = str(data["name"])

# First export the graph normally
output_file = "dish_ingredient_bipartite.gexf"
nx.write_gexf(B, output_file)

# Add actual Gephi visualization coordinates to the GEXF XML
tree = ET.parse(output_file)
root = tree.getroot()

ns = {"g": "http://www.gexf.net/1.2draft"}
viz_ns = "http://www.gexf.net/1.2draft/viz"

ET.register_namespace("", ns["g"])
ET.register_namespace("viz", viz_ns)

# Map exported node IDs to their coordinates
positions = {
    str(node): (float(data["x"]), float(data["y"]))
    for node, data in B.nodes(data=True)
}

for element in root.findall(".//g:nodes/g:node", ns):
    node_id = element.get("id")

    if node_id not in positions:
        continue

    x, y = positions[node_id]

    # Add Gephi's visualization position element
    position = ET.SubElement(
        element,
        f"{{{viz_ns}}}position"
    )
    position.set("x", str(x))
    position.set("y", str(y))
    position.set("z", "0.0")

tree.write(
    output_file,
    encoding="utf-8",
    xml_declaration=True
)

print(f"Gephi-ready graph saved: {output_file}")


# Debug check
sample_dishes = dish_nodes[:10]
sample_nodes = set(sample_dishes)

for dish in sample_dishes:
    sample_nodes.update(B.neighbors(dish))

S = B.subgraph(sample_nodes).copy()

dish_sample = [
    n for n, d in S.nodes(data=True)
    if d["bipartite"] == 0
]
ingredient_sample = [
    n for n, d in S.nodes(data=True)
    if d["bipartite"] == 1
]

pos = {
    n: (B.nodes[n]["x"], B.nodes[n]["y"])
    for n in S.nodes()
}

plt.figure(figsize=(18, 12))

nx.draw_networkx_nodes(
    S, pos, nodelist=dish_sample,
    node_color="skyblue", node_size=350, label="Dishes"
)

nx.draw_networkx_nodes(
    S, pos, nodelist=ingredient_sample,
    node_color="lightgreen", node_size=250, label="Ingredients"
)

nx.draw_networkx_edges(S, pos, alpha=0.35)

labels = {
    n: str(B.nodes[n]["name"])[:22]
    for n in S.nodes()
}

nx.draw_networkx_labels(S, pos, labels, font_size=7)

plt.title("Bipartite Dish–Ingredient Network")
plt.legend()
plt.axis("off")
plt.tight_layout()
plt.savefig("dish_ingredient_sample.png", dpi=200)
plt.show()
