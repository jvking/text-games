# Text-games
This repository provides text game simulators for research purposes.

### User-friendly version
If you just want to have a sense with what text-based games look like, you can try the following .html based version:
 - [Saving John](http://interactivestoryspace.appspot.com/final2_sjohn_jtsay.html)
 - [Machine of Death](http://ifarchive.giga.or.at/if-archive/games/competition2013/web/machineofdeath/MachineOfDeath.html)
 - [Fantasy World](http://horizondark.com:8000/webclient/) (Thanks to Karthik for providing the reference.)

### Python simulators (under text-games/simulators/, Dependencies: Python 2.7)
This directory contains three text game simulators, including **Saving John** and **Machine of Death** mentioned in [1], and **Fantasy World** mentioned in [2].

**Saving John** and **Machine of Death** are converted from their original .html source codes. They are stand-alone simulators and should be easy to run from text-games/simulators/.

**Fantasy World** requires installing the [Evennia package and text-world](https://github.com/mrkulk/text-world). The game is played in socket mode. If you are more familar with python, you don't have to install the Lua framework provided by [text-world-player](https://github.com/karthikncode/text-world-player). After you have installed both Evennia and text-world, the following steps should have been done to start the server and create the world:
 - On the server end, ./start.sh 1 # assuming we initiate only one game server
 - create superuser with username "root" and password "root"
 - On the client end, nc localhost 4001
 - connect root root
 - @batchcommand tutorial_world.build
 - @quell
 - quit the client connection

To run the game, simply:
```
python text-games/simulators/MySimulator.py --name savingjohn --doShuffle True
```
Note that the _name_ could be "savingjohn", "machineofdeath", or "fantasyworld". Setting the _doShuffle_ to True will randomly shuffle the list of actions every time they are presented. After typing the above command, you will see the following tuple of (state-text, list of action-texts, reward). The action order may differ:

>('It\'s difficult to breathe.     My psychiatrist says that in order to be saved, one must want to be saved. "Are you alright?" Cherie calls from the deck. The waves don\'t give me a chance to respond. Instinctively,  my eyes turn upward as I\'m being pulled under. Please, not yet. "John!"  I want a second chance. It\'s Cherie\'s hand, reaching out, but for some reason it slips  away. My mind\'s going in circles and I need to focus on  something, anything. I grab on to the first thought that  seems coherent:', ["I don't deserve to live.", "It's not her fault.", "She can't save me.", "She's trying to kill me!"], 0)

You can continue the game by typing your choice of action (in integer number). For example, typing 0 (choosing "I don't deserve to live.") at the above state will transition to the next tuple:

>('//"Knock, knock."//\\n//"Uh, who\'s there?"//\\n//"Orange."//\\n//"Hey, shut the fuck up over there!"//\\n//"Are you seriously telling --"//\\n//"I\'d like some oranges,"//\\n//"You don\'t deserve oranges,"//\\n//"Well you don\'t deserve to live!"//\\n//"Good one,"//\\n\\n//Someone laughs.//\\n\\n//"--knock knock jokes?"//\\n//"Orange you glad that I didn\'t kick your face in?"//\\n//"Catholic guilt at its best I suppose,"//\\n//"I need another shot..."//\\n//"Seriously, face palm,"//\\n\\nIt\'s the Fourth of July. I remember because it\'s the day I met \\nSam. "Uncle Sam\'s Birthday!" His nervous laughter was hard to \\nforget. \\n\\nHe wore an orange shirt with an orange slice on it, making him \\nthe joke of the party. I felt kind of bad for the guy; he left \\nthe party alone and no one could remember who had brought him \\nin the first place.\\n\\n', ['Continue'], 0)

You can edit the main function in MySimulator.py to hook up with your own agent and RL framework. The interface of all three text games are designed so that they share the same interface:
```
(text, actions, reward) = mySimulator.Read() # text is a string (state-text), actions is a list of strings, reward is a float
mySimulator.Act(playerInput)                 # playerInput is an integer or a string, depending on which game
mySimulator.Restart()                        # after the episode ends, restart the game
```

For *Machine of Death*, we also provide a paraphrased action mode. You can import MachineOfDeathSimulator and initialize a second simulator with "doParaphrase = True".

The _name_\_\*Id.pickle in text-games/simulators store the vocabulary of each game. _name_\_\*wordId.pickle means state-side vocabulary, and _name_\_\*actionId.pickle means action-side vocabulary.

### References
1. Ji He, Jianshu Chen, Xiaodong He, Jianfeng Gao, Lihong Li, Li Deng and Mari Ostendorf. [_Deep Reinforcement Learning with a Natural Language Action Space._](http://arxiv.org/abs/1511.04636) Association for Computational Linguistics (ACL). 2016.
2. Karthik Narasimhan, Tejas Kulkarni, Regina Barzilay. [_Language Understanding for Text-based Games Using Deep Reinforcement Learning._](http://aclweb.org/anthology/D/D15/D15-1001.pdf) Conference on Empirical Methods in Natural Language Processing (EMNLP). 2015.
