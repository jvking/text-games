#!/usr/bin/env python
# created by Ji He, Oct. 13th, 2015
# last modified by Ji He, Apr. 7th, 2016

from collections import Counter
import numpy as np
import random
import re
from scipy.sparse import csr_matrix
import sys

def Tokenize(myStr):
    # return a list of tokenized words
    return re.findall(r"[\w]+", myStr.lower())

class DataSample:
    def __init__(self, inputSize, outputSize):
        self.X = np.zeros((1, inputSize))
        self.action = None # action can take values in range(outputSize)
        self.next_reward = 0.0
        self.next_X = np.zeros((1, inputSize))

class DataSampleDrrn:
    def __init__(self, X1, X2s):
        self.X1 = X1
        self.X2s = X2s
        self.action = None # action can take values in range(len(X2s))
        self.next_reward = 0.0
        self.next_X1 = None
        self.next_X2s = []

def UpdateNextRewardState(data):
    for index, dataSample in enumerate(data[: -1]):
        if dataSample.action == None:
            data[index].next_reward = 0.0
            continue
        data[index].next_reward = data[index + 1].next_reward
        data[index].next_X = data[index + 1].X
    data[len(data) - 1].next_reward = 0.0
    return data

def UpdateNextRewardStateDrrn(data):
    for index, dataSample in enumerate(data[: -1]):
        if dataSample.action == None:
            data[index].next_reward = 0.0
            continue
        data[index].next_reward = data[index + 1].next_reward
        data[index].next_X1 = data[index + 1].X1
        data[index].next_X2s = data[index + 1].X2s
    data[len(data) - 1].next_reward = 0.0
    return data

def PreprocessTextVector(text, actionOptions, dict_wordId, dict_actionId, maxNumActions):
    # return: 1-by-(2258 + 419 * 9) matrix
    col_temp, value_temp = zip(*[(dict_wordId[key], value) for key, value in Counter(Tokenize(text)).iteritems() if key in dict_wordId]) if Tokenize(text) <> [] else ([], [])
    col = np.array(col_temp)
    my_value = np.array(value_temp)
    for idxAction, actionOption in enumerate(actionOptions):
        col_temp, value_temp = zip(*[(dict_actionId[key], value) for key, value in Counter(Tokenize(actionOption)).iteritems()]) if Tokenize(actionOption) <> [] else ([], [])
        # make input feature (2258 + 419 * 9)
        col_temp = np.add(col_temp, len(dict_wordId) + idxAction * len(dict_actionId))
        col = np.concatenate((col, col_temp), axis = 0)
        my_value = np.concatenate((my_value, np.array(value_temp)), axis = 0)
    row = np.zeros(len(col))
    return csr_matrix((my_value, (row, col)), shape = (1, len(dict_wordId) + len(dict_actionId) * maxNumActions))

def PreprocessTextList(text, actionOptions, dict_wordId, dict_actionId):
    # return: 1-by-2258 matrix, and list of 1-by-419 matrix
    col, my_value = zip(*[(dict_wordId[key], value) for key, value in Counter(Tokenize(text)).iteritems() if key in dict_wordId]) if Tokenize(text) <> [] else ([], [])
    col = np.array(col)
    my_value = np.array(my_value)
    row = np.zeros(col.shape)
    X1 = csr_matrix((my_value, (row, col)), shape = (1, len(dict_wordId)))

    X2s = []
    for idxAction, actionOption in enumerate(actionOptions):
        col, my_value = zip(*[(dict_actionId[key], value) for key, value in Counter(Tokenize(actionOption)).iteritems()]) if Tokenize(actionOption) <> [] else ([], [])
        col = np.array(col)
        row = np.zeros(col.shape)
        X2s.append(csr_matrix((my_value, (row, col)), shape = (1, len(dict_actionId))))

    return X1, X2s

def DumpData(mySimulator, dict_wordId, dict_actionId, myQLearner, dict_config = {"maxNumActions": 4, "numEpisode": 200, "exploration method": "softmax", "exploration parameter": 0.2, "fileOut": "expReplay1.txt"}):
    # dict_config = {"maxNumActions": 4, "numEpisode": 200, "exploration method": "epsilon", "exploration parameter": 0.1, "fileOut": "expReplay1.txt"}
    # Here dict_config["exploration"] can be either "epsilon" or "softmax"
    states, actions, rewards, next_states, terminals = [], [], [], [], []
    averageReward = []
    feature_dim = len(dict_wordId) + len(dict_actionId) * dict_config["maxNumActions"]
    outfile = open(dict_config["fileOut"], "w")
    outfile.write("episodeId\ttimeStepId\ttext\tactions\treward\n")
    for episodeId in range(dict_config["numEpisode"]):
        mySimulator.Restart()
        timeStepId = 0
        while True:
            (raw_text, raw_actions, reward) = mySimulator.Read()
            outfile.write(str(episodeId) + "\t" + str(timeStepId) + "\t" + raw_text + "\t")
            # let's first consider the simple [X1, X2s[0], X2s[1], X2s[2], zeros]
            state = PreprocessTextVector(raw_text, raw_actions, dict_wordId, dict_actionId, dict_config["maxNumActions"]).toarray()
            terminal = (len(raw_actions) == 0)
            if timeStepId <> 0:
                rewards.append(reward)
                next_states.append(state) # skip initial state, align to next state
                terminals.append(terminal)
            if terminal or timeStepId >= 250:
                outfile.write("\t" + str(reward) + "\t\n")
                averageReward.append(reward) # averageReward stores the terminal reward
                break
            else:
                action = myQLearner.choose_action(state, dict_config["exploration method"], dict_config["exploration parameter"], len(raw_actions))
                states.append(state)
                actions.append(action)
                outfile.write(str(action) + ":" + "**ACT**".join(raw_actions) + "\t" + str(reward) + "\t" + str(myQLearner.q_vals(state)[: len(raw_actions)]) + "\n")
            mySimulator.Act(action)
            # update data
            timeStepId += 1
    outfile.close()
    print("Average reward: %.5f" % np.mean(averageReward))
    return np.reshape(states, (len(states), feature_dim)), np.reshape(actions, (len(actions), 1)), np.reshape(rewards, (len(rewards), 1)), np.reshape(next_states, (len(next_states), feature_dim)), np.reshape(terminals, (len(terminals), 1)), np.mean(averageReward)

# this function dumps data using a simulator, following softmax action selection
# the return data will be a list of vectors, each vector is a concatenation of text and actions (BoW)
def DumpDataTextActionVector(storyName, mySimulator, dict_wordId, dict_actionId, maxNumActions, myQLearner, numEpisode, softmax_alpha, fileOut):
    outfile = open(fileOut, "w")
    outfile.write("episodeId\ttimeStepId\ttext\taction\treward\n")
    data = []
    averageReward = []

    for episodeId in range(numEpisode):
        mySimulator.Restart()
        timeStepId = 0
        while timeStepId < 500: # if the sequence is longer than 500, break
            # read in curState, and action options
            (text, actionOptions) = mySimulator.Read()
            outfile.write(str(episodeId) + "\t" + str(timeStepId) + "\t" + text + "\t")
            X = PreprocessTextVector(text, actionOptions, dict_wordId, dict_actionId, maxNumActions)

            dataSample = DataSample(len(dict_wordId) + len(dict_actionId) * maxNumActions, maxNumActions)
            dataSample.X = X
            if timeStepId == 499:
                dataSample.next_reward = -0
            else:
                dataSample.next_reward = AssignReward(text, storyName)

            if actionOptions <> []:
                # let's first do random
                # playerInput = np.random.randint(range(len(actionOptions)))
                #######################
                qvals = myQLearner.q_vals(X.toarray())[: len(actionOptions)] * softmax_alpha
                qvals -= np.max(qvals) # in order for np.exp(qvals) to be stable
                playerInput = np.where(np.random.multinomial(1, np.exp(qvals) / np.sum(np.exp(qvals))))[0][0]
                dataSample.action = playerInput
                outfile.write(str(playerInput) + ":" + "**ACT**".join(actionOptions) + "\t" + str(dataSample.next_reward) + "\t")
                # write out Q-values
                outfile.write(str(myQLearner.q_vals(X.toarray())[: len(actionOptions)]) + "\n")

            data.append(dataSample)
            if actionOptions == [] or "THE END" in text or timeStepId == 499:
                averageReward.append(dataSample.next_reward)
            if actionOptions == [] or "THE END" in text: # story ends
                outfile.write("\t" + str(dataSample.next_reward) + "\n")
                break
            # click action
            mySimulator.Act(playerInput)
            timeStepId = timeStepId + 1

    outfile.close()
    # update next_reward and next_X
    data = UpdateNextRewardState(data)

    # print out average reward, as evaluation
    print("Average reward: %.5f" % np.mean(averageReward))
    return data, np.mean(averageReward)

# this function dumps data using a simulator, following softmax action selection
# the return data will be a list of tuples, each tuple is a pair of text vector and list of actions (BoW)
def DumpDataTextActionList(storyName, mySimulator, dict_wordId, dict_actionId, maxNumActions, myQLearner, numEpisode, softmax_alpha, fileOut):
    outfile = open(fileOut, "w")
    outfile.write("episodeId\ttimeStepId\ttext\taction\treward\n")
    data = []
    averageReward = []

    for episodeId in range(numEpisode):
        mySimulator.Restart()
        timeStepId = 0
        while timeStepId < 500: # if the sequence is longer than 500, break
            # read in curState, and action options
            (text, actionOptions) = mySimulator.Read()
            outfile.write(str(episodeId) + "\t" + str(timeStepId) + "\t" + text + "\t")
            X1, X2s = PreprocessTextList(text, actionOptions, dict_wordId, dict_actionId)

            dataSample = DataSampleDrrn(X1, X2s)
            if timeStepId == 499: # the game did not finish
                dataSample.next_reward = -0
            else:
                dataSample.next_reward = AssignReward(text, storyName)

            if actionOptions <> []:
                qvals = myQLearner.model.fwdPass(X1, X2s, False) * softmax_alpha
                qvals -= np.max(qvals) # in order for np.exp(qvals) to be stable
                playerInput = np.where(np.random.multinomial(1, np.exp(qvals) / np.sum(np.exp(qvals))))[0][0]
                dataSample.action = playerInput
                outfile.write(str(playerInput) + ":" + "**ACT**".join(actionOptions) + "\t" + str(dataSample.next_reward) + "\t")
                # write out Q-values
                outfile.write(str(myQLearner.model.fwdPass(X1, X2s, False)) + "\n")

            data.append(dataSample)
            if actionOptions == [] or "THE END" in text or timeStepId == 499:
                averageReward.append(dataSample.next_reward)
            if actionOptions == [] or "THE END" in text: # story ends
                outfile.write("\t" + str(dataSample.next_reward) + "\n")
                break

            # click action
            mySimulator.Act(playerInput)
            timeStepId = timeStepId + 1

    outfile.close()
    # update next_reward and next_X
    data = UpdateNextRewardStateDrrn(data)

    # print out average reward, as evaluation
    print("Average reward: %.5f" % np.mean(averageReward))
    return data, np.mean(averageReward)
