import spacy
# from scipy import spatial
# tree = spatial.KDTree(A)

nlp = spacy.load('en_core_web_sm')
vecs = nlp.vocab.vectors

doc = nlp('To know is to forget that anything is possible.')



def most_similar(word):
    queries = [w for w in word.vocab if w.is_lower == word.is_lower and w.prob >= -15]
    by_similarity = sorted(queries, key=lambda w: word.similarity(w), reverse=True)
    return [ lex.text for lex in by_similarity[:10]]

final = ''
for token in doc:
    final = final +
