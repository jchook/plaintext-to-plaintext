import numpy as np
from scipy.spatial import KDTree

def load_glove_model(path, dim):
    f = open(path, 'r')
    xs = np.empty((0, dim))
    ys = []
    for line in f:
        splitLine = line.split()
        word = splitLine[0]
        embedding = [float(val) for val in splitLine[1:]]
        np.append(xs, [embedding], axis=0)
        ys.append(embedding)
    return (xs, ys)

def query_similar(vec, words, tree):
    return words[tree.query(vec)[0][0]]

print("Loading GloVe vectors...")
words, vecs = load_glove_model(
    '/data/pretrained/glove/glove.twitter.27B.25d.txt', 25
)

print("Loading search tree...")
tree = KDTree(vecs)

doc1 = ['to', 'know', 'is', 'to', 'forget', 'that', 'anything', 'is', 'possible']
doc2 = []

for word in doc1:
    key = words.index(word)
    doc2.append(query_similar(vec, words, tree))

print(doc2)