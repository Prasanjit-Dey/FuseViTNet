# -*- coding: utf-8 -*-
"""

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1mjjtUd7HWc7HHXMpKwbVzZ9hg4LIzjm3
"""

import numpy as np
import random
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
import tensorflow.keras.layers as L
from sklearn.model_selection import KFold
import tensorflow.keras.backend as K
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.metrics import RootMeanSquaredError
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import os
import gc
from tensorflow.keras.callbacks import ModelCheckpoint
from sklearn.model_selection import train_test_split

from google.colab import files
_ = files.upload()

!unzip O3.zip -d "O3"
from IPython.display import clear_output
clear_output(wait=False)
!rm O3.zip

files = pd.read_csv("/content/O3/O3/files.csv")

files

def pearson(y_true,y_pred):
  if len(y_true.shape)!=1:
    true = []
    for i in range(y_true.shape[0]):
      true.extend(y_true[i])
    pred = []
    for i in range(y_pred.shape[0]):
      pred.extend(y_pred[i])
  else:
    true=y_true
    pred=y_pred
  return np.mean((np.array(true)-np.mean(true))*(np.array(pred)-np.mean(pred)))/(np.std(np.array(true))*np.std(np.array(pred)))

def pearsonCorrAvgDays(true,pred):
  # assert len(true.shape)>=3,"true must have at least 3 dimensions, found {}".format(len(true.shape))
  assert true.shape==pred.shape, "true and pred must have same shape, found {} and {}".format(true.shape,pred.shape)
  scores = []
  for i in range(true.shape[0]):
    scores.append(pearson(true[i],pred[i]))
  return np.mean(scores),scores

def pearsonCorrAvgPixels(true,pred):
  scores = []
  for i in range(true.shape[1]):
    scores.append(pearson(true[:,i],pred[:,i]))
  return np.mean(scores),scores

def loadData(df,satdir = "/content/O3/O3/satellite/",gdir = "/content/O3/O3/ground/"):
  X = []
  Y = []
  for i in range(df.shape[0]):
    factor = 46*(6.02214/6.023)*1e2
    sat = np.expand_dims(factor*np.load(os.path.join(satdir,df["SatFile"].iloc[i])),axis=2)
    ground = np.load(os.path.join(gdir,df["GroundFile"].iloc[i])).flatten()
    if not np.isnan(np.sum(sat)) and not np.isnan(np.sum(ground)):
      if not np.std(ground)==0:
        X.append(sat)
        Y.append(ground)
  return np.stack(X,axis=0),np.stack(Y,axis=0)

# CNN Model
def build_model(X_train):
    inp = L.Input(shape=X_train[0].shape)
    h = L.Conv2D(16, (5, 5), activation="relu", padding="same")(inp)
    h = L.Conv2D(32, (5, 5), activation="relu")(h)
    h = L.MaxPooling2D(pool_size=(2, 2), strides=2)(h)
    h = L.Conv2D(16, (5, 5), activation="relu")(h)
    h = L.Conv2D(32, (5, 5), activation="relu")(h)
    out = L.Flatten()(h)
    out = L.Dense(50, activation="linear")(out)
    out = L.Dense(np.prod(X_train[0].shape), activation="linear")(out)
    model = Model(inputs=inp, outputs=out)
    model.compile(optimizer=Adam(learning_rate=0.01), loss="mse", metrics=[RootMeanSquaredError()])
    return model

#Model training
scores_list = []
rmses = []
maes = []

for fold in range(5):
  print("\nFold {}\n".format(fold))
  train_files = files[files["Fold"]!=fold]
  val_files = files[files["Fold"]==fold]

  X_train,Y_train = loadData(train_files)
  X_val,Y_val = loadData(val_files)
  # loss_plt = utils.loss_plt()
  K.clear_session()
  model = build_model(X_train)
  if fold==0:
    print(model.summary())
  ckpt = ModelCheckpoint(f"model_{fold}.hdf5",monitor="val_root_mean_squared_error",mode="min",save_best_only=True,save_weights_only=True)
  model.fit(X_train,Y_train,
            epochs=30,
            verbose=0,
            batch_size=8,
            validation_data = (X_val,Y_val),
            callbacks=[ckpt])
  model.load_weights(f"model_{fold}.hdf5")
  rmse = mean_squared_error(Y_val,model.predict(X_val),squared=False)
  rmses.append(rmse)
  mae = mean_absolute_error(Y_val,model.predict(X_val))
  maes.append(mae)

  print("Fold {} RMSE Score: {}".format(fold, rmse))
  print("Fold {} MAE Score: {}".format(fold, mae))
  s,ls = pearsonCorrAvgDays(Y_val,model.predict(X_val))
  print("Fold {} Pearson coeff avg over days: {}".format(fold,np.mean([i for i in ls if not pd.isnull(i)])))
  scores_list.append(ls)
  if fold!=4:
    del model
    _ = gc.collect()
print("\nCV RMSE Score: {}".format(np.mean(rmses)))
print("\nCV MAE Score: {}".format(np.mean(maes)))

from itertools import product

# Updated CNN Model
def build_model(X_train, kernel_size=(5, 5), activation_func="relu"):
    inp = L.Input(shape=X_train[0].shape)
    h = L.Conv2D(16, kernel_size, activation=activation_func, padding="same")(inp)
    h = L.Conv2D(32, kernel_size, activation=activation_func)(h)
    h = L.MaxPooling2D(pool_size=(2, 2), strides=2)(h)
    h = L.Conv2D(16, kernel_size, activation=activation_func)(h)
    h = L.Conv2D(32, kernel_size, activation=activation_func)(h)
    out = L.Flatten()(h)
    out = L.Dense(50, activation=activation_func)(out)
    out = L.Dense(np.prod(X_train[0].shape), activation=activation_func)(out)
    model = Model(inputs=inp, outputs=out)
    model.compile(optimizer=Adam(learning_rate=0.01), loss="mse", metrics=[RootMeanSquaredError()])
    return model


# Lists of hyperparameters to tune
batch_sizes = [8, 16, 32]
kernel_sizes = [(5, 5)]
activation_functions = ["linear", "gelu", "relu", "softmax", "tanh"]

# Lists to store results for each hyperparameter combination
all_results = []

for batch_size, kernel_size, activation_func in product(batch_sizes, kernel_sizes, activation_functions):
    scores_list = []
    rmses = []
    maes = []

    for fold in range(5):
        print("\nFold {}\n".format(fold))
        train_files = files[files["Fold"] != fold]
        val_files = files[files["Fold"] == fold]

        X_train, Y_train = loadData(train_files)
        X_val, Y_val = loadData(val_files)

        K.clear_session()
        model = build_model(X_train, kernel_size=kernel_size, activation_func=activation_func)

        # Modify batch size
        if batch_size != 8:
            model.fit(X_train, Y_train, epochs=30, verbose=0, batch_size=batch_size,
                      validation_data=(X_val, Y_val), callbacks=[ckpt])
        else:
            model.fit(X_train, Y_train, epochs=30, verbose=0,
                      validation_data=(X_val, Y_val), callbacks=[ckpt])

        model.load_weights(f"model_{fold}.hdf5")
        rmse = mean_squared_error(Y_val, model.predict(X_val), squared=False)
        rmses.append(rmse)
        mae = mean_absolute_error(Y_val, model.predict(X_val))
        maes.append(mae)
        pred1 = model.predict(X_val)
        print("Fold {} RMSE Score: {}".format(fold, rmse))
        print("Fold {} MAE Score: {}".format(fold, mae))
        s, ls = pearsonCorrAvgDays(Y_val, model.predict(X_val))
        print("Fold {} Pearson coeff avg over days: {}".format(fold, np.mean([i for i in ls if not pd.isnull(i)])))
        scores_list.append(ls)

        if fold != 4:
            del model
            _ = gc.collect()

    # Store results for the current hyperparameter combination
    avg_rmse = np.mean(rmses)
    avg_mae = np.mean(maes)
    avg_pearson = np.mean([np.mean([i for i in ls if not pd.isnull(i)]) for ls in scores_list])

    all_results.append({
        'batch_size': batch_size,
        'kernel_size': kernel_size,
        'activation_func': activation_func,
        'avg_rmse': avg_rmse,
        'avg_mae': avg_mae,
        'avg_pearson': avg_pearson
    })

# Display results for all hyperparameter combinations
for result in all_results:
    print("\nBatch Size: {}, Kernel Size: {}, Activation Function: {}".format(result['batch_size'],
                                                                               result['kernel_size'],
                                                                               result['activation_func']))
    print("Average RMSE: {}".format(result['avg_rmse']))
    print("Average MAE: {}".format(result['avg_mae']))
    print("Average Pearson Coefficient: {}".format(result['avg_pearson']))