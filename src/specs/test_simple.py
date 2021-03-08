from ..methods.simple import *

inputs = "ABACDACADADABADABAC"

pr = LastSuccessor()
for l in inputs:
    pr.push(l)
    print(pr.predict())
