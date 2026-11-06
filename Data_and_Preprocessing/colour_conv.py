# This code is authored by Claude, Raghav and Sasanska
# Used to make node colours as average of the recipes it is connected to and tries to implement polygonal nodes.
import pandas as pd
import networkx as nx

def add_viz_shapes(B,
                   shapes={0: "square", 1: "triangle"},   
                   polygon_sides={0: 4, 1: 3},            
                   colors={0: (41, 125, 195), 1: (204, 204, 204)},
                   sizes={0: 10.0, 1: 10.0}):
    # GExf generator
    for n, d in B.nodes(data=True):
        p = d["bipartite"]
        r, g, b = colors[p]
        d["Polygon"] = int(polygon_sides[p])              
        d["viz"] = {"shape": shapes[p],
                    "color": {"r": r, "g": g, "b": b, "a": 1.0},
                    "size": float(sizes[p])}
    return B




nodes = pd.read_csv("nodes_8.0.csv")
edges = pd.read_csv("edges_5.0.csv")

B = nx.Graph()

# Construct graph
for r in nodes.itertuples():
    B.add_node(
        r.Id,
        bipartite=0 if r.Type == "Recipe" else 1,
        label=r.Label,
        cuisine=r.Cuisine,
        type=r.Type,
        Color=r.Color
    )

B.add_edges_from(
    edges[["Source", "Target"]].itertuples(
        index=False, name=None
    )
)

recipes = {
    n for n, d in B.nodes(data=True)
    if d["bipartite"] == 0
}

ingredients = set(B) - recipes

assert nx.is_bipartite(B)


# Hex <-> RGB conversion
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(
        int(hex_color[i:i+2], 16)
        for i in (0, 2, 4)
    )


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


# Assign original colours to all nodes
for n in B.nodes:
    rgb = hex_to_rgb(B.nodes[n]["Color"])

    viz = B.nodes[n].setdefault("viz", {})
    viz["color"] = {
        "r": rgb[0],
        "g": rgb[1],
        "b": rgb[2],
        "a": 1.0
    }


# Average Recipe colours for each Ingredient
for ingredient in ingredients:

    connected_recipes = [
        n for n in B.neighbors(ingredient)
        if n in recipes
    ]

    if not connected_recipes:
        continue

    colours = [
        hex_to_rgb(B.nodes[n]["Color"])
        for n in connected_recipes
    ]

    avg_rgb = tuple(
        round(sum(c[i] for c in colours) / len(colours))
        for i in range(3)
    )

    avg_hex = rgb_to_hex(avg_rgb)

    # Update hex attribute
    B.nodes[ingredient]["Color"] = avg_hex

    # Update Gephi visualization colour
    B.nodes[ingredient]["viz"]["color"] = {
        "r": avg_rgb[0],
        "g": avg_rgb[1],
        "b": avg_rgb[2],
        "a": 1.0
    }


# Add your existing shapes
B = add_viz_shapes(B)

nx.write_gexf(B, "recipes_ingredients.gexf")