import pickle

with open("spam_classifier.pkl", "wb") as f:
    pickle.dump(model, f)
