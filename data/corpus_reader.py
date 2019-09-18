def read_file(filename):
    lines = [line.rstrip('\n') for line in open(filename)]
    dataset = []
    sentence = []
    for i in range(len(lines)):
        if(len(lines[i]) == 0):
            dataset.append(sentence);
            sentence = []
            continue
        if(lines[i][0] == '#'):
            continue
        tags = lines[i].split(' ')
        word = (tags[0],tags[1])
        sentence.append(word)
    return dataset
        

if __name__ == "__main__":
    pass 