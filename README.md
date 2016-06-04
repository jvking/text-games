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
Note that the _name_ could be "savingjohn", "machineofdeath", or "fantasyworld". After typing the above command, you will see the following tuple of (state-text, list of action-texts, reward). The action order may differ:

>('It\'s difficult to breathe.     My psychiatrist says that in order to be saved, one must want to be saved. "Are you alright?" Cherie calls from the deck. The waves don\'t give me a chance to respond. Instinctively,  my eyes turn upward as I\'m being pulled under. Please, not yet. "John!"  I want a second chance. It\'s Cherie\'s hand, reaching out, but for some reason it slips  away. My mind\'s going in circles and I need to focus on  something, anything. I grab on to the first thought that  seems coherent:', ["I don't deserve to live.", "It's not her fault.", "She can't save me.", "She's trying to kill me!"], 0)

### References
1. Ji He, Jianshu Chen, Xiaodong He, Jianfeng Gao, Lihong Li, Li Deng and Mari Ostendorf. [_Deep Reinforcement Learning with a Natural Language Action Space._](http://arxiv.org/abs/1511.04636) Association for Computational Linguistics (ACL). 2016.
2. Karthik Narasimhan, Tejas Kulkarni, Regina Barzilay. [_Language Understanding for Text-based Games Using Deep Reinforcement Learning._](http://aclweb.org/anthology/D/D15/D15-1001.pdf) Conference on Empirical Methods in Natural Language Processing (EMNLP). 2015.
