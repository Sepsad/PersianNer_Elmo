# -*- coding: utf-8 -*-
"""NER with Elmo.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rkqUDQpLvcUQPU5XBjTvbv9gBIDUImN7
"""
import data.corpus_reader as corpus_reader
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow_hub as hub
from keras import backend as K
from keras.models import Model, Input
from keras.layers.merge import add
from keras.layers import LSTM, Embedding, Dense, TimeDistributed, Dropout, Bidirectional, Lambda
from sklearn.preprocessing import LabelBinarizer 
from sklearn.metrics import classification_report
from itertools import chain

def sent2words(sents):
  words = []
  for p in sents:
    words.append(p[0])
  return words

def sent2tags(sents):
  tags = []
  for p in sents:
    tags.append(p[1])
  return tags

def process_data(data, max_len):
  sents = []
  tags = []
  for s in data:
    sent_i = []
    tags_i = []
    for i in range(max_len):
      try:
        tags_i.append(tag2idx[s[i][1]])
        sent_i.append(s[i][0])
      except:
        tags_i.append(tag2idx["O"])
        sent_i.append("PAD")
    tags.append(tags_i)
    sents.append(sent_i)
  return sents, tags

def ElmoEmbedding(x):
    return elmo_model(inputs={
                            "tokens": tf.squeeze(tf.cast(x, 'string')),
                            "sequence_len": tf.constant(batch_size*[max_len])
                      },
                      signature="tokens",
                      as_dict=True)["elmo"]

def bio_classification_report(y_true, y_pred):
  """
  Classification report for a list of BIO-encoded sequences.
  It computes token-level metrics and discards "O" labels.

  Note that it requires scikit-learn 0.15+ (or a version from github master)
  to calculate averages properly!
  """
  lb = LabelBinarizer()
  y_true_combined = lb.fit_transform(list(chain.from_iterable(y_true)))
  y_pred_combined = lb.transform(list(chain.from_iterable(y_pred)))

  tagset = set(lb.classes_) - {'O'}
  tagset = sorted(tagset, key=lambda tag: tag.split('-', 1)[::-1])
  class_indices = {cls: idx for idx, cls in enumerate(lb.classes_)}

  return classification_report(
    y_true_combined,
    y_pred_combined,
    labels = [class_indices[cls] for cls in tagset],
    target_names = tagset,
  )

def predict_tags(y_pred):
  out = []
  for i in range(len(y_pred)):
    out_i = []
    for j in range(len(y_pred[i])):
      out_i.append(tags[y_pred[i][j]])
    out.append(out_i)
  return out

if __name__ = "__main__":  
  train = corpus_reader.read_file("data/train.txt")
  dev = corpus_reader.read_file("data/dev.txt")
  test = corpus_reader.read_file("data/test.txt")

  words = []
  tags = []
  for s in train + dev + test:
    words.extend(sent2words(s))
    tags.extend(sent2tags(s))

  words = list(set(words))
  tags = list(set(tags))

  words.append("ENDPAD")

  n_words = len(words)
  n_tags = len(tags)

  tag2idx = {t: i for i, t in enumerate(tags)}
  idx2tag = {p[1]: p[0] for p in tag2idx.items()}

  max_len = 150

  sents_tr, tags_tr = process_data(train, max_len)
  sents_dv, tags_dv = process_data(dev, max_len)
  sents_te, tags_te = process_data(test, max_len)

  batch_size = 32
  sess = tf.Session()
  K.set_session(sess)

  elmo_model = hub.Module("https://tfhub.dev/google/elmo/2", trainable=True)
  sess.run(tf.global_variables_initializer())
  sess.run(tf.tables_initializer())

  input_text = Input(shape=(max_len,), dtype='string')
  embedding = Lambda(ElmoEmbedding, output_shape=(max_len, 1024))(input_text)
  x = Bidirectional(LSTM(units=512, return_sequences=True,
                         recurrent_dropout=0.2, dropout=0.2))(embedding)
  x_rnn = Bidirectional(LSTM(units=512, return_sequences=True,
                             recurrent_dropout=0.2, dropout=0.2))(x)
  x = add([x, x_rnn])  # residual connection to the first biLSTM
  out = TimeDistributed(Dense(n_tags, activation="softmax"))(x)

  X_tr, y_tr = sents_tr[:(len(sents_tr)//batch_size)*batch_size] , tags_tr[:(len(sents_tr)//batch_size)*batch_size]
  X_dv, y_dv = sents_dv[:(len(sents_dv)//batch_size)*batch_size] , tags_dv[:(len(sents_dv)//batch_size)*batch_size]
  X_te, y_te = sents_te[:(len(sents_te)//batch_size)*batch_size] , tags_te[:(len(sents_te)//batch_size)*batch_size]

  y_tr = np.array(y_tr).reshape(np.array(y_tr).shape[0], np.array(y_tr).shape[1], 1)
  y_dv = np.array(y_dv).reshape(np.array(y_dv).shape[0], np.array(y_dv).shape[1], 1)

  model = Model(input_text, out)
  model.compile(optimizer="adam", loss="sparse_categorical_crossentropy")

  history = model.fit(np.array(X_tr), np.array(y_tr), validation_data=(np.array(X_dv), np.array(y_dv)), 
                   batch_size=batch_size, epochs=10, verbose=1)

  pred = model.predict(np.array(X_te))
  pred = np.argmax(pred, axis=-1)
  y_te_pred = predict_tags(pred)

  y_te = [[idx2tag[t] for t in s] for s in y_te]

  print(bio_classification_report(y_te, y_te_pred))