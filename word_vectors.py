from tqdm import tqdm
import numpy as np
import subprocess
import re
import os
import mmap

def load_vectors(filename='/media/nate/Windows/github/glove_vectors/glove.6B.50d.txt'):
    """
    Loads GloVe vectors from file.
    """
    # can use this part to get filename from args
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--vectors_file', default='~/glove.840B.300d.txt', type=str)
    # args = parser.parse_args()
    # filename = agrs.vectors_file

    with open(filename, 'r') as f:
        vectors = {}
        tq = tqdm(total=os.path.getsize(filename), unit='B', unit_scale=True)
        for line in f:
            vals = line.rstrip().split(' ')
            vectors[vals[0]] = np.array([float(x) for x in vals[1:]])
            tq.update(len(line))

    return vectors

if __name__ == "__main__":
    vectors = load_vectors()
