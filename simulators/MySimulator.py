#!/usr/bin/env python
# -*- coding: utf-8 -*-
# created by Ji He, Aug. 19th, 2015
# last modified by Ji He, Apr. 7th, 2016

import argparse
from collections import defaultdict
import HTMLParser
import numpy as np
import operator
import os
#import pdb; pdb.set_trace()
try:
    import cPickle as pickle
except:
    import pickle
import random
import re
import socket
import sys
import time

curDirectory = os.path.dirname(os.path.abspath(__file__))

class MyHTMLParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.data = []

    def handle_data(self, data):
        self.data.append(data)

    def MyHTMLFilter(self, myStr):
        self.data = []
        self.feed(myStr)
        return " ".join(self.data)

class StoryNode:
    def __init__(self, text, actions, links):
        self.text = text # text is what shown to player
        self.actions = actions # actions are what shown to player
        self.links = links # links are internal links direct to next node.tag

def AssignReward(ending, story = "savingjohn"):
    if story.lower() == "fantasyworld":
        if "REWARD_" in ending:
            return(float(re.search(r"\[REWARD_.*? : (.*?)\]", ending).group(1)))
        if "not available" in ending or "not find" in ending or "You can't get that." in ending or "you cannot" in ending or "splinter is already burning" in ending or "is no way" in ending or "not uproot them" in ending: # invalid command
            return(-1.0)
        return(-0.01)
    if story.lower() == "savingjohn":
        if ending.startswith("Submerged under water once more, I lose all focus."):
            return(-10)
        if ending.startswith("Honest to God, I don't know what I see in her."):
            return(10)
        if ending.startswith("Suddenly I can see the sky."):
            return(20)
        if ending.startswith("Suspicion fills my heart and I scream."):
            return(-20)
        if ending.startswith("Even now, she's there for me."):
            return(0)
    if story.lower() == "machineofdeath":
        if not """THE END""" in ending:
            return(-0.1)
        if """You spend your last few moments on Earth lying there, shot through the heart, by the image of Jon Bon Jovi.""" in ending:
            return(-20)
        if """You may be locked away for some time.""" in ending:
            return(-10)
        if """Eventually you're escorted into the back of a police car as Rachel looks on in horror.""" in ending:
            return(-10)
        if """You can't help but smile.""" in ending:
            return(20)
        if """Fate can wait.""" in ending:
            return(-10)
        if """you hear Bon Jovi say as the world fades around you.""" in ending:
            return(-20)
        if """Hope you have a good life.""" in ending:
            return(20)
        if """As the screams you hear around you slowly fade and your vision begins to blur, you look at the words which ended your life.""" in ending:
            return(-20)
        if """Sadly, you're so distracted with looking up the number that you don't notice the large truck speeding down the street.""" in ending:
            return(-10)
        if """Stay the hell away from me!&quot; she blurts as she disappears into the crowd emerging from the bar.""" in ending:
            return(10)
        if """Congratulations!""" in ending:
            return(20)
        if """All these hiccups lead to one grand disaster.""" in ending:
            return(-10)
        if """After all, it's your life. It's now or never. You ain't gonna live forever. You just want to live while you're alive.""" in ending:
            return(30)
        if """Rachel waves goodbye as you begin the long drive home. After a few minutes, you turn the radio on to break the silence.""" in ending:
            return(20)
    return (0)

""" Starting actual simulators """
class FantasyWorldSimulator:
    # before connecting to the server, the following steps should have been done:
    # ./start.sh 1
    #  - create superuser root:root
    # nc localhost 4001
    # connect root root
    # @batchcommand tutorial_world.build
    # @quell
    # quit

    def __init__(self, file_actionId = os.path.join(curDirectory, "fantasyworld_actionId.pickle")):
        self.title = "FantasyWorld"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ansi_escape = re.compile(r'\x1b[^m]*m')
        print >>sys.stderr, 'connecting to %s port %s' % ('localhost', 4001)
        self.sock.connect(('localhost', 4001))
        # self.sock.settimeout(1.0)
        # self.sock.recv(5000)
        # self.sock.sendall("create root root")
        data = self.sock.recv(5000)
        self.sock.sendall("connect root root")
        data = self.sock.recv(5000)
        self.sock.sendall("tutorial")
        data = self.sock.recv(5000)
        self.sock.sendall("begin adventure")
        self.Restart()

        with open(file_actionId, "r") as infile:
            self.list_actions = list(pickle.load(infile))

    def Restart(self):
        data = self.sock.recv(5000)
        self.sock.sendall("@teleport tut#02") # teleport to Cliff by the coast
        data = self.sock.recv(5000)
        self.sock.sendall("look")
        self.bridge_passed = False
        return

    def Read(self):
        data = self.sock.recv(5000)
        while not "<EOM>" in data:
            data += self.sock.recv(5000)
        text = re.sub(r'\xff\xf1', '', re.sub(r'\r\n', r'\n', self.ansi_escape.sub('', data))) # plain text version
        if "Exits: " in text and "root covered wall" not in text:
            list_actions = re.findall("Exits: (.*?)(?:$|\n)", text)[-1].split(r", ")
        else:
            list_actions = self.list_actions
        # return data # colored version
        reward = AssignReward(text, "fantasyworld")
        if "REWARD_bridge" in text:
            if self.bridge_passed == False:
                self.bridge_passed = True
            else:
                reward = -0.01
        if "it must be the goal you" in text: # story ends
            list_actions = []
        return (text, list_actions, reward)

    def Act(self, playerInput):
        self.sock.sendall(playerInput)
        return

    def Close(self):
        self.sock.close()


class SavingJohnSimulator:
    def __init__(self, doShuffle, storyFile = os.path.join(curDirectory, "savingjohn.pickle")):
        self.title = "SavingJohn"
        self.storyPlot = {}
        self.startTiddler = ""
        with open(storyFile, "r") as infile:
            self.storyPlot, self.startTiddler = pickle.load(infile)

        self.doShuffle = doShuffle # whether actions are shuffled when they are Read()
        self.idxShuffle = []

        self.storyNode = None
        self.Restart()

    def Restart(self):
        self.tiddler = self.startTiddler
        self.storyNode = self.storyPlot[self.tiddler]
        self.params_path = ""

    def Read(self):
        if self.storyNode.text.startswith("A wet strand of hair hinders my vision and I'm back in the water."):
            if self.doShuffle:
                self.idxShuffle = range(2)
                random.shuffle(self.idxShuffle)
            idxTemp = 0
            if self.params_path == "Adam": idxTemp = 1
            elif self.params_path == "Sam": idxTemp = 2
            elif self.params_path == "Lucretia": idxTemp = 3
            elif self.params_path == "Cherie": idxTemp = 4

            actionsTemp = list(operator.itemgetter(0, idxTemp)(self.storyNode.actions))
            return (self.storyNode.text, [actionsTemp[i] for i in self.idxShuffle] if self.doShuffle else actionsTemp, AssignReward(self.storyNode.text, "savingjohn"))

        if self.doShuffle:
            self.idxShuffle = range(len(self.storyNode.actions))
            random.shuffle(self.idxShuffle)
        return (self.storyNode.text, [self.storyNode.actions[i] for i in self.idxShuffle] if self.doShuffle else self.storyNode.actions, AssignReward(self.storyNode.text, "savingjohn"))

    def Act(self, playerInput):
        # if shuffled actions, find actual action index
        playerInput = self.idxShuffle[playerInput] if self.doShuffle else playerInput

        if self.storyNode.text.startswith("A wet strand of hair hinders my vision and I'm back in the water.") and playerInput <> 0:
            if self.params_path == "Adam": playerInput = 1
            elif self.params_path == "Sam": playerInput = 2
            elif self.params_path == "Lucretia": playerInput = 3
            elif self.params_path == "Cherie": playerInput = 4

        self.tiddler = self.storyNode.links[playerInput]
        self.storyNode = self.storyPlot[self.tiddler]

        if self.tiddler == "Adam1.6": self.params_path = "Adam"
        elif self.tiddler == "Sam10": self.params_path = "Sam"
        elif self.tiddler == "Lucretia10": self.params_path = "Lucretia"
        elif self.tiddler == "Cherie7": self.params_path = "Cherie"
        elif self.tiddler == "Adam8": self.params_path = "Adam"
        elif self.tiddler == "Sam9": self.params_path = "Cherie"
        elif self.tiddler == "Lucretia7": self.params_path = "Cherie"
        return


class MachineOfDeathSimulator:
    def __init__(self, doShuffle, doParaphrase = False):
        self.title = "MachineOfDeath"
        self.Restart()
        self.methodDict = {}
        self.methodDict["Cut off"] = self.tiddler0
        self.methodDict["Sarah"] = self.tiddler1
        self.methodDict["There's a light"] = self.tiddler2
        self.methodDict["Nights"] = self.tiddler164
        self.methodDict["Explain"] = self.tiddler4
        self.methodDict["Holy crap, I can't believe that worked"] = self.tiddler110
        self.methodDict["Your goose is cooked!"] = self.tiddler6
        self.methodDict["Leap"] = self.tiddler7
        self.methodDict["Suicide"] = self.tiddler98
        self.methodDict["Look out below"] = self.tiddler9
        self.methodDict["Keep running"] = self.tiddler137
        self.methodDict["Wigs"] = self.tiddler11
        self.methodDict["Not over until the chiselled rocker sings"] = self.tiddler43
        self.methodDict["Untitled Passage 2"] = self.tiddler15
        self.methodDict["No"] = self.tiddler100
        self.methodDict["Watch"] = self.tiddler16
        self.methodDict["SHOT THROUGH THE HEART BY BON JOVI"] = self.tiddler17
        self.methodDict["Knock, knock!"] = self.tiddler18
        self.methodDict["Tackle"] = self.tiddler19
        self.methodDict["StoryTitle"] = self.tiddler20
        self.methodDict["Wait"] = self.tiddler21
        self.methodDict["Shoot"] = self.tiddler22
        self.methodDict["Whew!"] = self.tiddler135
        self.methodDict["Bar"] = self.tiddler23
        self.methodDict["Eating a sinner"] = self.tiddler24
        self.methodDict["LOOKING UP NOTES"] = self.tiddler25
        self.methodDict["Gone home"] = self.tiddler26
        self.methodDict["Leave"] = self.tiddler28
        self.methodDict["Blood"] = self.tiddler172
        self.methodDict["Up your alley"] = self.tiddler29
        self.methodDict["Couldn't have known"] = self.tiddler30
        self.methodDict["That song was terrible"] = self.tiddler31
        self.methodDict["Yell"] = self.tiddler32
        self.methodDict["He drinks"] = self.tiddler33
        self.methodDict["TODO"] = self.tiddler34
        self.methodDict["Waiting together"] = self.tiddler35
        self.methodDict["Sinner"] = self.tiddler36
        self.methodDict["Outside the karaoke bar"] = self.tiddler37
        self.methodDict["Unjabbed"] = self.tiddler195
        self.methodDict["Eat eat eat"] = self.tiddler38
        self.methodDict["The hard truth"] = self.tiddler40
        self.methodDict["Gotta go fast!"] = self.tiddler41
        self.methodDict["Nothing to hide"] = self.tiddler130
        self.methodDict["Play to win"] = self.tiddler44
        self.methodDict["Did you forget he's not real?"] = self.tiddler45
        self.methodDict["Gunless"] = self.tiddler46
        self.methodDict["From my cold, dead hands"] = self.tiddler47
        self.methodDict["Blonde"] = self.tiddler48
        self.methodDict["Kitchen"] = self.tiddler76
        self.methodDict["Inside car"] = self.tiddler49
        self.methodDict["Shoo"] = self.tiddler51
        self.methodDict["Quit"] = self.tiddler52
        self.methodDict["Lister"] = self.tiddler53
        self.methodDict["Excused"] = self.tiddler54
        self.methodDict["Reveal"] = self.tiddler55
        self.methodDict["Bedroom drawers"] = self.tiddler56
        self.methodDict["Standing your ground"] = self.tiddler57
        self.methodDict["Axe to grind"] = self.tiddler58
        self.methodDict["AB"] = self.tiddler177
        self.methodDict["In da house"] = self.tiddler59
        self.methodDict["Sit on it"] = self.tiddler193
        self.methodDict["Drink up"] = self.tiddler60
        self.methodDict["The choice"] = self.tiddler61
        self.methodDict["See no evil"] = self.tiddler62
        self.methodDict["Losing smile"] = self.tiddler63
        self.methodDict["Rescue"] = self.tiddler64
        self.methodDict["So clean"] = self.tiddler65
        self.methodDict["Eating a floater"] = self.tiddler66
        self.methodDict["Eating a lister"] = self.tiddler67
        self.methodDict["Explore"] = self.tiddler68
        self.methodDict["Wake"] = self.tiddler69
        self.methodDict["One on one"] = self.tiddler70
        self.methodDict["On the beach"] = self.tiddler50
        self.methodDict["Goose!"] = self.tiddler72
        self.methodDict["A message"] = self.tiddler73
        self.methodDict["Stairs"] = self.tiddler74
        self.methodDict["Splat"] = self.tiddler75
        self.methodDict["Thanks"] = self.tiddler27
        self.methodDict["A slip of paper"] = self.tiddler77
        self.methodDict["Sir"] = self.tiddler151
        self.methodDict["David"] = self.tiddler79
        self.methodDict["OLD AGE NOTES"] = self.tiddler80
        self.methodDict["The meeting"] = self.tiddler81
        self.methodDict["Hell cab"] = self.tiddler82
        self.methodDict["Ignition"] = self.tiddler83
        self.methodDict["Axe"] = self.tiddler84
        self.methodDict["Butt"] = self.tiddler71
        self.methodDict["Ignore"] = self.tiddler85
        self.methodDict["Run, run"] = self.tiddler86
        self.methodDict["Standing in a mall"] = self.tiddler87
        self.methodDict["Photo"] = self.tiddler39
        self.methodDict["Meeting 1"] = self.tiddler89
        self.methodDict["LOOKING UP"] = self.tiddler90
        self.methodDict["OLD AGE"] = self.tiddler91
        self.methodDict["Snatched"] = self.tiddler92
        self.methodDict["Bedroom"] = self.tiddler93
        self.methodDict["StoryAuthor"] = self.tiddler94
        self.methodDict["Yes"] = self.tiddler95
        self.methodDict["You first"] = self.tiddler96
        self.methodDict["Brunette"] = self.tiddler188
        self.methodDict["SWERVE"] = self.tiddler97
        self.methodDict["Death"] = self.tiddler8
        self.methodDict["Closet"] = self.tiddler14
        self.methodDict["No thanks"] = self.tiddler78
        self.methodDict["BON JOVI NOTES"] = self.tiddler101
        self.methodDict["Teeth"] = self.tiddler103
        self.methodDict["Poison"] = self.tiddler104
        self.methodDict["Start"] = self.tiddler105
        self.methodDict["Returns"] = self.tiddler106
        self.methodDict["Exit"] = self.tiddler107
        self.methodDict["Meeting"] = self.tiddler108
        self.methodDict["Doggy with a gun"] = self.tiddler109
        self.methodDict["Cupboard"] = self.tiddler111
        self.methodDict["Dive"] = self.tiddler112
        self.methodDict["Killing time"] = self.tiddler152
        self.methodDict["Rank"] = self.tiddler114
        self.methodDict["Phone"] = self.tiddler115
        self.methodDict["Making a stool of yourself"] = self.tiddler116
        self.methodDict["UFO Catcher"] = self.tiddler117
        self.methodDict["Floater"] = self.tiddler118
        self.methodDict["Ain't worth it"] = self.tiddler119
        self.methodDict["Rumbly tummy"] = self.tiddler120
        self.methodDict["Diarroiah"] = self.tiddler121
        self.methodDict["Eating an A.B."] = self.tiddler155
        self.methodDict["Card"] = self.tiddler123
        self.methodDict["Reveal to Rachel"] = self.tiddler124
        self.methodDict["Sofahh"] = self.tiddler125
        self.methodDict["Reflection"] = self.tiddler126
        self.methodDict["Gotten me killed"] = self.tiddler127
        self.methodDict["Stealth eater"] = self.tiddler128
        self.methodDict["Time to talk"] = self.tiddler129
        self.methodDict["Gun"] = self.tiddler131
        self.methodDict["Outta here"] = self.tiddler132
        self.methodDict["The drive home"] = self.tiddler133
        self.methodDict["Busted"] = self.tiddler134
        self.methodDict["Drinking tea together"] = self.tiddler5
        self.methodDict["Waiting in the kitchen"] = self.tiddler136
        self.methodDict["Beneath"] = self.tiddler10
        self.methodDict["Logo"] = self.tiddler185
        self.methodDict["Painting"] = self.tiddler138
        self.methodDict["Uninterested"] = self.tiddler139
        self.methodDict["Something foyer"] = self.tiddler140
        self.methodDict["Crazy"] = self.tiddler141
        self.methodDict["Streets"] = self.tiddler143
        self.methodDict["BREAK"] = self.tiddler144
        self.methodDict["Meeting 2"] = self.tiddler145
        self.methodDict["Still crazy"] = self.tiddler146
        self.methodDict["Duck"] = self.tiddler147
        self.methodDict["TIME TRAVEL MISHAP"] = self.tiddler148
        self.methodDict["Sure do"] = self.tiddler149
        self.methodDict["Not this time"] = self.tiddler150
        self.methodDict["Continue meeting"] = self.tiddler88
        self.methodDict["Pee freely"] = self.tiddler113
        self.methodDict["Showtime!"] = self.tiddler153
        self.methodDict["Menu"] = self.tiddler154
        self.methodDict["Time to go"] = self.tiddler122
        self.methodDict["Dressing time"] = self.tiddler156
        self.methodDict["Looking"] = self.tiddler157
        self.methodDict["Outside"] = self.tiddler158
        self.methodDict["Calm"] = self.tiddler159
        self.methodDict["Not at all"] = self.tiddler160
        self.methodDict["Winning smile"] = self.tiddler161
        self.methodDict["Attack!"] = self.tiddler162
        self.methodDict["Sing a song"] = self.tiddler163
        self.methodDict["Her"] = self.tiddler99
        self.methodDict["Restaurant"] = self.tiddler167
        self.methodDict["Poster"] = self.tiddler165
        self.methodDict["YOU'RE A TERRIBLE PERSON"] = self.tiddler166
        self.methodDict["Dress to impress"] = self.tiddler3
        self.methodDict["Photos"] = self.tiddler169
        self.methodDict["Meaning"] = self.tiddler170
        self.methodDict["Dismantle and dispose"] = self.tiddler171
        self.methodDict["Knocked his block off!"] = self.tiddler168
        self.methodDict["Drive off"] = self.tiddler173
        self.methodDict["Ask"] = self.tiddler174
        self.methodDict["A cold kitchen"] = self.tiddler175
        self.methodDict["Why"] = self.tiddler176
        self.methodDict["Your move!"] = self.tiddler12
        self.methodDict["Lost"] = self.tiddler178
        self.methodDict["Later"] = self.tiddler179
        self.methodDict["No pee for me!"] = self.tiddler180
        self.methodDict["Drawers"] = self.tiddler181
        self.methodDict["Gun grab"] = self.tiddler182
        self.methodDict["The Machine"] = self.tiddler183
        self.methodDict["Co-workers"] = self.tiddler184
        self.methodDict["Table"] = self.tiddler142
        self.methodDict["Drink tea"] = self.tiddler186
        self.methodDict["Why the dive?"] = self.tiddler187
        self.methodDict["Wrestle"] = self.tiddler42
        self.methodDict["Life after Sarah"] = self.tiddler189
        self.methodDict["Fuck"] = self.tiddler190
        self.methodDict["Pantry"] = self.tiddler191
        self.methodDict["Another"] = self.tiddler192
        self.methodDict["The beginning"] = self.tiddler102
        self.methodDict["Yet another"] = self.tiddler194
        self.methodDict["What a rotten way to die"] = self.tiddler13
        self.methodDict["Sloppy eater"] = self.tiddler196
        self.methodDict["Leave meeting"] = self.tiddler197
        self.methodDict["Floordrobe"] = self.tiddler198
        self.methodDict["The door"] = self.tiddler199

        self.doShuffle = doShuffle # whether actions are shuffled when they are Read()
        self.myHTMLParser = MyHTMLParser()
        
        self.doParaphrase = doParaphrase
        if self.doParaphrase:
            actions_orig = [self.myHTMLParser.MyHTMLFilter(line.rstrip()) for line in open(os.path.join(curDirectory, "machineofdeath_originalActions.txt"), "r")]
            actions_para = [self.myHTMLParser.MyHTMLFilter(line.rstrip()) for line in open(os.path.join(curDirectory, "machineofdeath_paraphrasedActions.txt"), "r")]
            self.dict_paraphrase = {action_orig: action_para for action_orig, action_para in zip(actions_orig, actions_para)}

    def Restart(self):
        self.current_tiddler = "Start"
        self.params = defaultdict(int)

    def Read(self):
        self.text = """"""
        self.current_links = []
        self.actions = []
        self.methodDict[self.current_tiddler]()
        self.text = re.sub("\\n", " ", self.myHTMLParser.MyHTMLFilter(self.text))
        self.actions = [re.sub("\\n", " ", self.myHTMLParser.MyHTMLFilter(action)) for action in self.actions]
        if self.doShuffle:
            self.idxShuffle = range(len(self.actions))
            random.shuffle(self.idxShuffle)
        if "THE END" in self.text: # the story ends
            self.idxShuffle = []
            self.actions = []
        if self.doParaphrase:
            self.actions = [self.dict_paraphrase[action] if action in self.dict_paraphrase else action for action in self.actions]
        return (self.text, [self.actions[i] for i in self.idxShuffle] if self.doShuffle else self.actions, AssignReward(self.text, "machineofdeath"))

    def Act(self, playerInput):
        playerInput = self.idxShuffle[playerInput] if self.doShuffle else playerInput
        self.current_tiddler = self.current_links[playerInput]
        return

    def tiddler0(self):
        self.text += """"""
        self.current_links += []
        self.actions += []
        self.methodDict["Look out below"]()
        return

    def tiddler1(self):
        self.text += """&quot;My wife, Sarah.&quot; He says as he points to a photo of a woman. He silently stares at it for a few moments. &quot;The horse is named Henry. We had another one called Susan, too. She loved those horses, even made wigs from their hair when she had enough from trimming ‘em.&quot;\n\nHe pauses to drink some more of his tea. &quot;I'll be the first to admit she was an odd one, but I loved that woman. She made me happier than I thought possible. Not a day goes by where I don't miss 'er.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.params['sarah'] = 2
        self.methodDict["Time to talk"]()
        return

    def tiddler2(self):
        self.text += """You struggle towards the light with all your remaining strength.\n\nIt's emitting from a house.\n\nYou slam open the door and collapse inside, the world fading around you.\n\n\n"""
        self.current_links += ['Wake']
        self.actions += ['...']
        return

    def tiddler3(self):
        self.text += """You find and iron your most trusted outfit and slip it on. You take a gander at yourself in the mirror and feel confident, until you remember that you're running late.\n\nThis is no time for self-appreciation!\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 5
        self.params['dressedWell'] = 1
        self.methodDict["Rumbly tummy"]()
        return

    def tiddler4(self):
        self.text += """You explain your dire situation to the old man, who reveals his name to be John.\n\n"""
        if self.params['axeAsk'] == 0:
            self.text += """&quot;Alright,&quot; he says with a sniff. &quot;The storm knocked out the phone line. The weather's died down enough that the CB Radio in my truck might work.&quot;"""
        if self.params['axeAsk'] == 1:
            self.text += """&quot;Alright,&quot; he says with a sniff. &quot;As for the axe, I was out choppin’ firewood. I'm not sure if you've noticed, but it's bloody cold.\n\n&quot;The storm knocked out the phone line. The weather's died down enough that the CB Radio in my truck might work.&quot;"""
        self.text += """\n\nHe opens the door you crashed through earlier, and before closing it behind him, looks you in the eye and says &quot;Stay right there. And don't touch anything.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.params['returnVar'] = 0
        self.methodDict["Kitchen"]()
        return

    def tiddler5(self):
        self.text += """You drink from your mug while keeping an eye on the man opposite you.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["He drinks"]()
        return

    def tiddler6(self):
        self.text += """You quickly dive to the floor, knocking over the standee in the process. The man stares at it with menace in his eyes, and snarls &quot;You.&quot; \n\nHe points the gun at the standee and fires. The bullet goes straight through the cardboard and into you.\n\nYou spend your last few moments on Earth lying there, shot through the heart, by the image of Jon Bon Jovi.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler7(self):
        self.text += """Your attempt to leap over Sarah's desk is foiled by your own foot getting caught on the ledge, sending you face first onto the floor, scattering papers in all directions in the process. You quickly stand up and dust yourself off.\n\n&quot;Sorry, Sarah.&quot;\n\n&quot;You're insane,&quot; she replies, doing a bad job of hiding her irritation as she gathers up the papers. &quot;Just get to the meeting.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Meeting"]()
        return

    def tiddler8(self):
        if self.params['oldAge'] == 1 and self.params['lookingUp'] == 1 and self.params['jovi'] == 1:
            self.params['oldAge'] = 0
            self.params['lookingUp'] = 0
            self.params['jovi'] = 0
        if self.params['firstDeathGiven'] == 1:
            if self.params['oldAge'] <> 0 and self.params['lookingUp'] <> 0 and self.params['jovi'] == 0:
                self.methodDict['SHOT THROUGH THE HEART BY BON JOVI']()
            if self.params['oldAge'] <> 0 and self.params['lookingUp'] == 0:
                self.methodDict['LOOKING UP']()
            if self.params['oldAge'] == 0:
                self.methodDict['OLD AGE']()
        if self.params['firstDeathGiven'] == 0:
            self.params['firstDeathGiven'] = 1
            self.params['firstDeath'] = int(np.floor(np.random.random() * 3 + 1))
            if self.params['firstDeath'] == 1:
                self.methodDict['LOOKING UP']()
            if self.params['firstDeath'] == 2:
                self.methodDict['OLD AGE']()
            if self.params['firstDeath'] == 3:
                self.methodDict['SHOT THROUGH THE HEART BY BON JOVI']()
        self.current_links += []
        self.actions += []
        return

    def tiddler9(self):
        self.text += """As you move forward, the people surrounding you suddenly look up with terror in their faces, and flee the street.\n\n\n\n"""
        self.current_links += ['Whew!', 'Splat']
        self.actions += ['Look up.', 'Ignore the alarm of others and continue moving forward.']
        return

    def tiddler10(self):
        self.text += """You lift the table cloth up and peek under it. You see what are clearly blood stains, smudged as if someone attempted to remove them with little success.\n\nYou put the cloth back down.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['lookCloth'] = 1
        self.methodDict["Kitchen"]()
        return

    def tiddler11(self):
        self.text += """You walk over to the pair of wigs, each sitting on a stand. One is blonde and the other is brunette."""
        self.current_links += ['Blonde', 'Brunette']
        self.actions += ['blonde', 'brunette']
        return

    def tiddler12(self):
        self.text += """He grabs the nearest chair and starts flailing it wildly around! &quot;Turn the music off!&quot; he screams. &quot;I'm not ready yet!&quot;\n\n\n\n\n"""
        self.current_links += ['Knocked his block off!', 'Goose!', 'Knock, knock!']
        self.actions += ['Use Bon Jovi as a shield!', 'Duck! DUCK!', 'Try to knock the chair from his hands!']
        return

    def tiddler13(self):
        self.text += """Suddenly, John begins to choke. He slams his hands on the desk as the choking becomes more violent and he begins to struggle, knocking over his mug in the process, the coffee spilling all over the table cloth which it proceeds to burn straight through.\n\n&quot;What the hell did you do t-,&quot; John’s sentence is interrupted by a stream of vomit erupting from his mouth. He lunges at you and wraps his hands around your neck before collapsing to the floor.\n\nThe Rescue Services burst through the front door, stopping in their tracks as they see the lifeless body on the floor before looking at you.\n\nYou may be locked away for some time.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['A cold kitchen', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler14(self):
        self.text += """You search through the closest and find nothing but old clothes and some fishing gear.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Bedroom"]()
        return

    def tiddler15(self):
        self.text += """"""
        self.current_links += []
        self.actions += []
        return

    def tiddler16(self):
        if self.params['chatted'] == 0:
            self.text += """You stand back and watch others approach the machine. A male who looks to be in his mid-to-late twenties approaches the machine, shaking. \n\nHe inserts a coin, has his finger jabbed, and picks up the ticket that's printed shortly afterwards. With reluctance, he reads it and a wave of relief rolls across his body. He wipes sweat from his brow and walks away, still a little shaken, but not stirred.\n\n&quot;Doing a bit of deathspotting, huh?&quot; You turn around and see a young woman, maybe not even quite in her twenties, with azure blue hair and red rimmed glasses, and sporting a simple, black work uniform.\n\nDeathspotting?\nYeah.\nNah."""
            self.current_links += ['Ask', 'Yes', 'No']
            self.actions += ['Deathspotting?', 'Yeah.', 'Nah.']
        if self.params['chatted'] == 1:
            self.text += """\nYou stand back and wait for others to approach the machine, but it appears the death rush is over. No one comes.\n\nReturn your eyes to the mall.&lt;&lt;endif&gt;&gt;\n"""
            self.current_links += ['Standing in a mall']
            self.actions += ['Return your eyes to the mall.']
        return

    def tiddler17(self):
        self.text += """You insert your finger, wince slightly at the jab, then pick up and read the card that’s quickly spat out.\n\n&lt;html&gt;&lt;h1&gt;&lt;center&gt;SHOT THROUGH THE HEART BY BON JOVI&lt;/center&gt;&lt;/h1&gt;\n&lt;html&gt;&lt;h4&gt;&lt;center&gt;YEARS LATER...&lt;/center&gt;&lt;/h4&gt;&lt;/html&gt;\nYou finally arrive at Rachel's house, a two-story villa overlooking the beach. Well, it actually belongs to her father, but he lets her have this one since he has another three dotted along the coast.\n\nRachel is what some people call a &quot;trust fund kid.&quot; Despite her wealth, she still has a job, which is how you met her. Your desk is across from hers.\n\nSome of your other co-workers warned you about her, describing her as a bit of a wild one. But &quot;weird&quot; and &quot;crazy&quot; are often words boring people use to describe interesting ones.\n\nBut hey, she invited you out with some of her friends, and you could do with a fun night out. It's been far too long since the last one.\n\nYou pull up into the drive way and approach the front door.\n"""
        self.current_links += ['In da house']
        self.actions += ['Knock.']
        self.params['waitForRach'] = 0
        self.params['jovi'] = 1
        self.params['joviPlayed'] = 1
        self.params['toldRachel'] = 0
        self.params['saidCrazy'] = 0
        self.params['saidGun'] = 0
        self.params['saidSing'] = 0
        self.params['saidExcused'] = 0
        return

    def tiddler18(self):
        self.text += """You slam your entire weight against the man, making him stumble backwards and drop the chair to the ground as a group of patrons race to restrain him.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Outta here"]()
        return

    def tiddler19(self):
        self.text += """You launch yourself at Jon Bon Jovi and tackle him to the ground! It's at this point you realise that it's only a cardboard standee. You stand up and look around. Everyone is silently staring at you with wide eyes.\n\n&quot;Uh, haha, my friend is a really huge fan of Jovi!” Rachel nervously explains. &quot;Just had to hug him!&quot; An &quot;Ooh!&quot; sweeps over the crowd and they return to their merry ways.\n\n&quot;What the hell was that?&quot; asks Rachel, clearly trying to restrain anger.\n\n\n\n"""
        self.current_links += ['Reveal to Rachel', 'Sit on it']
        self.actions += ['Tell her about your death.', 'Apologise and sit down at a table with her.']
        return

    def tiddler20(self):
        self.text += """Machine of Death"""
        self.current_links += []
        self.actions += []
        return

    def tiddler21(self):
        if self.params['carWait'] == 0:
            self.text += """You sit in the car and wait patiently. Snow continues to storm outside with no signs of stopping soon."""
        if self.params['carWait'] == 1:
            self.text += """You spend more time sitting in the car and waiting patiently. The snow storm carries on outside with no signs of relenting.\n\n\n\n\n\n"""
        self.current_links += ['Wait', 'Phone', 'Ignition', 'Outside']
        self.actions += ['Wait.', 'Try using your mobile phone.', 'Try starting the car.', 'Go outside.']
        self.params['carWait'] = 1
        return

    def tiddler22(self):
        self.text += """You pull the gun from the back of your pants, aim between Jon Bon Jovi's eyes, and pull the trigger.\n\nA bullseye. Jovi falls against the wall. Strangely, his expression doesn't seem to change at all.\n\nBy the time you realise it was only a cardboard standee, you've already been tackled to the ground by several patrons. Eventually you're escorted into the back of a police car as Rachel looks on in horror.\n\nYou better start livin’ on a prayer about getting off lightly.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler23(self):
        self.text += """You get out of your car and enter the bar with Rachel. The sound of a trio of women singing a drunken rendition of Wannabe by the Spice Girls hits you like a brick in the face.\n\nAfter the initial aural shock wears off, you look around and examine your surroundings. It is quite possibly the tackiest bar you've ever been in. There's low lighting, pictures of famous singers cover the wall, Christmas lights arranged into flower and love heart shapes hang from the ceiling, and it's a little sticky where you're standing.\n\nThat said, it doesn't appear to be the dangerous, scum-dwelling establishment its exterior suggests. It’s full of joyous people drinking, swaying and singing.\n\nYou take a moment to relish the drunken merriment. Then, in a corner, you see rock idol Jon Bon Jovi.\n\n"""
        if self.params['gun'] == 1:
            self.current_links += ['Shoot']
            self.actions += ['Shoot him before he has the chance to strike!']
        self.current_links += ['Tackle', 'Duck', 'Ignore']
        self.actions += ['Tackle him to the ground!', 'Duck! DUCK!', 'Ignore him.']
        return

    def tiddler24(self):
        self.text += """Some consider the sandwich a form of self inflicted punishment to atone for past sins. Others believe it's a delicious delicacy.\n\nYou're not sure which camp you fall in, but are ever so slightly leaning towards the former.\n\n"""
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        self.params['coins'] = self.params['coins'] - 2
        return

    def tiddler25(self):
        self.text += """looking up to someone\nlooking someone up\n\nif you quit, you end up going to someone you look up to but they cant you into a lot of trouble\n\nsomeone knocks you off with their scooter, its tempting to chase after her and boot her off her scooter, but you must stay focused\n\nadd a little bit of random chance to the quest"""
        self.current_links += []
        self.actions += []
        return

    def tiddler26(self):
        self.text += """You begin the long walk back home. On the way, you walk past the sign that almost ended your life, now partly responsible for prompting you to change it. \n\n&quot;Things are looking up!&quot;\n\nYou can't help but smile.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/center&gt;&lt;/html&gt;\n"""
        self.current_links += ['Later', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        self.params['meeting'] = 0
        self.params['timePassed'] = 0
        return

    def tiddler27(self):
        self.text += """&quot;I thought so, considering your hands.&quot; You look down at them and realise they're shaking.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["On the beach"]()
        return

    def tiddler28(self):
        self.text += """You take one last look at the machine and decide that, at least for today, you’re content with not adding the knowledge of your inevitable demise to your purchases.\n\nFate can wait.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/center&gt;&lt;/html&gt;"""
        self.current_links += []
        self.actions += []
        return

    def tiddler29(self):
        self.params['alleyRandom'] = 0
        self.params['alleyRandom'] = int(np.floor(np.random.random() * 2 + 1))
        if self.params['alleyRandom'] == 1:
            self.params['timePassed'] = self.params['timePassed'] - 2
            self.text += """You dash down the alley. Brilliant! There's no loading truck! You move to the next street with ease.\n"""
        if self.params['alleyRandom'] == 2:
            self.params['timePassed'] = self.params['timePassed'] + 3
            self.text += """You dash down the alley. Damn! There's a loading truck! You slowly navigate around it, receive odd looks from the delivery people, and move down to the next street.\n"""
        if self.params['timePassed'] <= 25:
            self.text += """You let out a sigh of relief when you come out to the street and see the bus coming towards you. You hope on, and it eventually drops you off outside the office.\n\n"""
            self.methodDict['Something foyer']()
        else:
            self.text += """You emerge from the street only to see the bus driving off in the distance. You were too slow! \n\nYou could dash down to a main street while looking up the number of a taxi company in your phone, and arrange for someone to drive you to the building. Or just forget about it and move on with your life.\n\n"""
            self.params['timeToGo'] = 30 - self.params['timePassed']
            if self.params['timeToGo'] > 0:
                self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
            if self.params['timeToGo'] == 0:
                self.text += """You're about to be late!"""
            if self.params['timeToGo'] < 0:
                self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!"""
            self.current_links += ['Hell cab', 'Gone home']
            self.actions += ['Call a cab. (One minute)', 'Call it quits.']
        return

    def tiddler30(self):
        self.text += """&quot;I know,&quot; she says. &quot;But I still feel a little bad. Tonight was supposed to be fun!&quot; She stares out of the passenger window. “What a disaster.”\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["A message"]()
        return

    def tiddler31(self):
        self.text += """This is no time for hunger games! You stride past the vendor and down the street, a sense of determination in each step you take.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 1
        self.params['ateFood'] = 0
        self.methodDict["Busted"]()
        return

    def tiddler32(self):
        self.params['busRandom'] = 0
        self.params['busRandom'] = int(np.floor(np.random.random() * 49 + 1))
        if self.params['busRandom'] == 25:
            self.methodDict["Holy crap, I can't believe that worked"]()
        if self.params['busRandom'] <> 25:
            self.methodDict['Not this time']()
        self.text += """"""
        self.current_links += []
        self.actions += []
        return

    def tiddler33(self):
        self.text += """He lifts the mug to his lips and takes a few large gulps before placing it back on the table, his hands wrapped around it.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Time to talk"]()
        return

    def tiddler34(self):
        self.text += """TODO:\n1. Add better descriptions for tasting food\n2. If player wins dinosaur, have it make cameo appearances in each story\n3. Add better responses to losing and winning dinosaur\n5. poison, burn poison die of smoke poison\n6. boredom, lie in your death bed, have lal these skilsl but never shared your life with anyone\n7. add random flavour text to the mall scene (THIS SCENE)\n8. death that makes you arrogant and end up with you killing another person\n9. maybe make alternate story for waiting in the car in OLD AGE. get stranded, end up losing a foot, at the end talk about all the stories you can make up for the old folks home?\n\n7. cop game\nfirst level kinda like barrack or qix, capture people then smog them, next level like lesbian spider wueens, chase after people and taser them, another level you run around and destroy occupy camp as fast as possible, another level a stealth game where you have to get money without being noticed. all levels about companies paying you or the government off to do what they want, ie getting rid of occupy as they are ruining business and stuff"""
        self.current_links += []
        self.actions += []
        return

    def tiddler35(self):
        self.text += """You do nothing but wait and keep an eye on the man opposite you.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["He drinks"]()
        return

    def tiddler36(self):
        self.text += """The Sinner's Sandwich. Freshly shaved slices of turkey, strawberry jam and a smatter of honey nut cornflakes between two slices of bread.\n"""
        if self.params['coins'] < 2:
            self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;Tragically (or perhaps luckily), you're not carrying enough money to experience this culinary curiosity."""
        if self.params['coins'] >= 2:
            self.current_links += ['Eating a sinner']
            self.actions += ['Buy one for two dollars.']
        self.current_links += ['Menu']
        self.actions += ['See what else is on offer.']
        return

    def tiddler37(self):
        self.text += """You drive past a billboard advertising the latest Machine of Death. Some clever graffiti makes it read &quot;Death to the Machine of Death.&quot; It looks like you've wandered into one of THOSE neighbourhoods.\n\nYou eventually arrive at the bar, which appears to be the kind of questionable repute. Half the lights of its neon name tag aren't functioning, the bin outside is overflowing, and a row of motorcycles are lined up next to it.\n\n&quot;I've no idea what I'm going to sing first,&quot; Rachel excitedly mutters to no one in particular as she hurries out of the car and towards the bar’s entrance.\n\nYou almost impulsively dash after her, when you suddenly remember something. In your glove box is a gun"""
        if self.params['win'] == 1:
            self.text += """ (currently being safely guarded by your Wee Rex Adorable Plush"""
        self.text += """, which you keep handy for all potential Bon Jovi related emergencies.\n\n\n\n"""
        self.current_links += ['Gun', 'Gunless']
        self.actions += ['Take the gun.', 'Leave the gun.']
        return

    def tiddler38(self):
        self.text += """You throw money at the vendor, which frankly is a rather rude thing to do, and order a tofu dog topped with mango chutney.\n\n\n\n\n"""
        self.current_links += ['Sloppy eater', 'Stealth eater']
        self.actions += ['No time to lose! Jam it in your mouth! (Two minutes)', "Just because you're in a hurry doesn't mean you have to lose your dignity! Eat it carefully! (Three minutes)"]
        self.params['ateFood'] = 1
        return

    def tiddler39(self):
        self.text += """You look at the photo on the bedside table. It shows what appears to be a young couple on their wedding day. The kind of wedding from a different era, say, fifty or so years ago.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Bedroom"]()
        return

    def tiddler40(self):
        self.text += """Shock shatters the miniature rock star's face before it’s quickly replaced with anger. &quot;That sort of talk isn't going to help my recovery at all! You're bad medicine. And bad medicine is not what I need.&quot;\n\nHe gives you a little growl, then walks over to his bed, curls up, and sends you the cutest death stare before falling asleep, moments before Rachel bounds down the stairs with her usual energy.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Time to go"]()
        return

    def tiddler41(self):
        self.text += """You sprint after the bus, but it just feels like it keeps slipping further away!\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 1
        self.methodDict["Streets"]()
        return

    def tiddler42(self):
        self.text += """You grab the gun and try to wrestle it from the man's hands, only to hear a loud BANG before you fall backwards into the standee and onto the floor.\n\nYou spend your last few moments on Earth lying there, shot through the heart, by the image of Jon Bon Jovi.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler43(self):
        self.text += """A man walking past you suddenly halts and screams &quot;STOP!&quot; at the top of his lungs. It's effective; though the music keeps playing, all the people in the bar turn to look at him.\n\n"""
        if self.params['gun'] == 1:
            self.methodDict['Gun grab']()
        if self.params['gun'] == 0:
            self.methodDict['Your move!']()
        self.current_links += []
        self.actions += []
        return

    def tiddler44(self):
        self.params['winRandom'] = int(np.floor(np.random.random() * 9 + 1))
        if self.params['winRandom'] == 5:
            self.params['win'] = 1
            self.text += """You manoeuvre the crane over the tiny dino, lower and clasp the jaws around it, and lift it back up... and have it safely dropped down the chute! Score!\n"""
        if self.params['winRandom'] <> 5 and self.params['win'] == 0:
            self.text += """You manoeuvre the crane over the tiny dino, lower and clasp the jaws around it, and lift it back up... only for it to fall from the crane’s frustratingly weak grasp. Curses! Foiled again, like yesterday’s ham!\n"""
        self.params['coins'] = self.params['coins'] - 1
        if self.params['coins'] == 0 and self.params['win'] == 0:
            self.text += """Sadly, you don't have any change left to try to win the dazzling dinosaur again."""
        if self.params['coins'] > 0 and self.params['win'] == 0:
            self.current_links += ['Play to win']
            self.actions += ['Try again!']
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler45(self):
        self.text += """You grab Jovi and hold him out in front of you at arm’s length. The man stares at it with menace in his eyes, snarling &quot;You.&quot; \n\nHe points the gun at the standee and fires. The bullet goes straight through the cardboard and into you.\n\nYou fall to the ground. You spend your last few moments on Earth lying there, shot through the heart, by the image of Jon Bon Jovi.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler46(self):
        self.text += """You decided that you don't need a firearm. You already have a set of guns sitting below your shoulders, after all.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['gun'] = 0
        self.methodDict["Bar"]()
        return

    def tiddler47(self):
        self.text += """You safely stow the gun in your jacket.\n\nYou hear the scampering of little feet behind you and turn to see Bon Jovi joyously run to the shore, playfully running towards and away from the waves as they move in and out before he comes up to you.\n\n&quot;Hello, Bon Jovi,&quot; you say.\n\n&quot;Hello!&quot; he responds.\n\nYou crouch down and give him a pat, only for your gun to fall from your jacket and onto the sand. Before you get a chance to pick it up, Bon Jovi picks it up in his mouth.\n\n&quot;Lookth what I foundth!&quot; he excitedly exclaims before a loud bang rings out across the beach.\n\n&quot;Oopth,&quot; you hear Bon Jovi say as the world fades around you.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler48(self):
        self.text += """The hair of this wig is a white blonde, and is rough to touch. It’s quite long, just above shoulder length. Underneath the wig stand is a label that reads &quot;Susan.&quot;\n\n\n\n"""
        self.current_links += ['Brunette', 'Bedroom']
        self.actions += ['Examine the brunette wig.', 'Examine the rest of the bedroom.']
        return

    def tiddler49(self):
        if self.params['car'] == 0:
            self.text += """After a few moments of dealing with the shock, you move your chair back to give yourself some space and assess your situation. Looking out the windows, you see nothing but snow and darkness. """
            if self.params['win'] == 1:
                self.text += """A glace down at the passenger seat reveals that your Wee Rex has fallen from his distinguished position on the dashboard. """
            self.text += """\n\nWell, this is a rather unfortunate situation. Not life threatening - at least, not to you - but tedious nonetheless. Still, better try find a way out of this predicament."""
        if self.params['car'] == 1:
            self.text += """You get back in the car, still stuck in a pickle."""
        if self.params['car'] == 0:
            self.params['car'] = 1
        self.current_links += ['Phone', 'Ignition', 'Wait', 'Outside']
        self.actions += ['Try using your mobile phone.', 'Try starting the car.', 'Wait.', 'Get out of car.']
        return

    def tiddler50(self):
        self.text += """You wander down to the beach with Rachel. It's a serene scene, with the moonlight shimmering on the ocean, the waves gently lapping the sand.\n\n&quot;At least we'll have a story to tell at work, I guess,&quot; Rachel suggests.\n\n\n\n"""
        self.current_links += ['Why the dive?', 'Nights']
        self.actions += ['\xe2\x80\x9cWhat do you see in a place like that?\xe2\x80\x9d', '\xe2\x80\x9cIs this how all your nights end up?\xe2\x80\x9d']
        return

    def tiddler51(self):
        self.text += """Shock shatters the miniature rock star's face before it’s quickly replaced with hurt. You almost feel like apologising, but before you can, Bon Jovi stares you straight in the eyes and says &quot;Don't. The damage is done.&quot;\n\nWith his head lowered, he slowly trundles off to his bed, curls up, and gives you puppy dog eyes before falling asleep, moments before Rachel bounds down the stairs with her usual energy.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Time to go"]()
        return

    def tiddler52(self):
        self.text += """&quot;Fine,&quot; he responds. &quot;Don't let the door hit you on the way out, because I don't want ass prints on my door.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.params['fired'] = 1
        self.methodDict["Later"]()
        return

    def tiddler53(self):
        self.text += """The Lister sandwich. Take one slice of bread. Throw a fried egg on it and smother it with fruit chutney. Stack on another piece of bread and throw a fried egg on top, this time smothered in chilli sauce. Seal the deal with a final slice of bread.\n"""
        if self.params['coins'] < 2:
            self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;Tragically (or perhaps luckily), you're not carrying enough money to experience this culinary curiosity."""
        if self.params['coins'] >= 2:
            self.current_links += ['Eating a lister']
            self.actions += ['Buy one for two dollars.']
        self.current_links += ['Menu']
        self.actions += ['See what else is on offer.']
        return

    def tiddler54(self):
        self.text += """You excuse yourself and move away from the dog. &quot;Don't be a little runaway!&quot; Bon Jovi insists. &quot;We ain't gonna live forever! Stay and talk!&quot;\n"""
        if self.params['waitForRach'] == 3:
            self.text += """&lt;html&gt;&lt;/p&gt;&lt;/html&gt; Both you and Bon Jovi become distracted by Rachel bounding down the stairs with her usual energy.\n"""
        self.params['saidExcused'] = 1
        if self.params['waitForReach'] <> 3:
            if self.params['saidCrazy'] == 0:
                self.current_links += ['Crazy']
                self.actions += ['&quot;I must be going crazy.&quot;']
            if self.params['saidGun'] == 0:
                self.current_links += ['Doggy with a gun']
                self.actions += ["&quot;You don't happen to know how to use a gun, do you?&quot;"]
            if self.params['saidSing'] == 0:
                self.current_links += ['Sing a song']
                self.actions += ['&quot;Care to sing one of your classics?&quot;']
            self.current_links += ['Shoo']
            self.actions += ['&quot;Shoo.&quot;']
            self.params['waitForRach'] = self.params['waitForRach'] + 1
        return

    def tiddler55(self):
        self.text += """Once everyone leaves the room, you approach David and show him your card.\n\nDavid scoffs. &quot;Do you know what my death card says? Poison!&quot; he yells, not even giving you a chance to guess. &quot;Do you know what that means?&quot;\n\n\n\n\n"""
        self.current_links += ['Meaning', 'Meaning', 'Meaning']
        self.actions += ['&quot;Your penchant for oysters is going to turn sour?&quot;', "&quot;You're going to be poisoned by a disgruntled employee?&quot;", "&quot;You're going to get hit by Poison's tour bus?&quot;"]
        return

    def tiddler56(self):
        self.text += """You rummage through the drawers, finding nothing but old clothes until you find a small, thin slip of cardboard buried at the bottom of one.\n\nIt's a death card.\n\n\n\n"""
        self.current_links += ['Card', 'Bedroom']
        self.actions += ['Read the card.', 'Examine the rest of the bedroom.']
        return

    def tiddler57(self):
        self.text += """You stand in the middle of the room and wait.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["The meeting"]()
        return

    def tiddler58(self):
        self.params['axeAsk'] = 1
        self.text += """ He seems taken aback by the implied accusation. &quot;No,&quot; he replies, his voice as cold as the snow outside. &quot;First you tell me what the devil you're doing in ‘ere.&quot;\n\n\n"""
        self.current_links += ['Explain']
        self.actions += ['Explain your situation.']
        return

    def tiddler59(self):
        self.text += """Before you even finish knocking, Rachel almost rips the door from its hinges.  &quot;Hey, come in!&quot; she excitedly shrills, her blonde hair dancing on her shoulders, where they meet the top of a long, understated black dress. You greet and follow her into the lounge room, which is about the size of a restaurant. A large restaurant. It's complete with a bar and ludicrously large entertainment system.\n\nShe gestures about the room as she hastily walks towards the stairs. &quot;Sit wherever you like!&quot; she insists.\n\n\n\n\n"""
        self.current_links += ['Sofahh', 'Making a stool of yourself', 'Standing your ground']
        self.actions += ['Sit on a sofa.', 'Sit on a barstool.', 'Remain standing.']
        return

    def tiddler60(self):
        self.text += """You lift the warm mug to your lips and take a small sip of hot tea.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Time to talk"]()
        return

    def tiddler61(self):
        self.text += """As she walks off, you feel the weight of the gun press against you.\n\nYou think about that crazed man at the bar, and how easily it could have been you. People call Rachel the crazy one, but you're the one carrying a gun around in case you bump into members of Bon Jovi!\n\n\n\n"""
        self.current_links += ['Dismantle and dispose', 'From my cold, dead hands']
        self.actions += ["It's time to let it go. Dismantle the gun to the best of your ability and get rid of it.", "Things could have gone a lot worse tonight. Who knows when I'll need that gun to survive!"]
        return

    def tiddler62(self):
        self.text += """You quickly grab the gun, stash it in your jacket, and close the glove box.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["The drive home"]()
        return

    def tiddler63(self):
        self.text += """You squeeze some toothpaste into your mouth and combine it with water, swivel the mixture around for a bit, then spit it out.\n\nWell, that should take care of your breath. You'll just have to remember not to smile too much.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 1
        self.params['brushedTeeth'] = 0
        self.methodDict["Dressing time"]()
        return

    def tiddler64(self):
        self.text += """You hear a knock at the door. John gets up to open it and welcomes in a couple of rescue workers. They bring some equipment over to check your well-being and lend you some crutches to help you get around.\n\nBefore you leave, you turn around to thank John but he's nowhere to be seen. Then he walks out of the bedroom, carrying some fishing gear.\n\nHe looks over to you and nods. &quot;Nice to meet ya. Hope you have a good life.&quot;\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['A cold kitchen', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler65(self):
        self.text += """You give your body the scrub down it so desperately needs, running a flannel over every bump and diving deep into every crevice, and eventually emerge from the shower minty fresh.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 8
        self.params['showered'] = 1
        self.methodDict["Teeth"]()
        return

    def tiddler66(self):
        self.text += """And now you understand why it's advised to eat them while drunk. At least the peas had some nutrients, making it the closest thing Deady's have to a healthy meal.\n\n\n\n"""
        self.params['coins'] = self.params['coins'] - 4
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler67(self):
        self.text += """The trick to a Lister Sandwich is to eat it before the bread disintergrates. It makes you feel like you're having a baby.\n\n\n"""
        self.params['coins'] = self.params['coins'] - 2
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler68(self):
        self.text += """You head out and trudge through the snow, trying to find some immediate assistance. After a short while, you turn around and see you've already lost sight of your car, your tracks leading back covered by snow.\n\n&quot;Hmm,&quot; you think to yourself.\n\n\n\n\n\n"""
        self.current_links += ['Lost', 'Lost', 'Lost', 'Lost']
        self.actions += ['Go east.', 'Go west.', 'Go north.', 'Go south.']
        return

    def tiddler69(self):
        self.text += """As you groggily regain consciousness sometime later, you look up through your dazed eyes and can't help but feel alarmed by the stranger standing over you with an axe.\n\n\n"""
        self.current_links += ['Attack!']
        self.actions += ['Defend yourself!']
        return

    def tiddler70(self):
        self.text += """John comes out of the bedroom visibly irritated, closes the door behind them, and sits opposite you at the table.\n\n\n\n"""
        self.current_links += ['Waiting together', 'Drinking tea together']
        self.actions += ['Wait.', 'Drink tea.']
        return

    def tiddler71(self):
        self.text += """David seems taken aback by your unexpected response. After a few brief moments of awkward silence, he finally responds with a flat &quot;Just do some work.&quot;\n\nYou proceed to do so.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Later"]()
        return

    def tiddler72(self):
        self.text += """You quickly duck, narrowly avoiding getting your noggin knocked off by a chair swinging through the air. Moments later, a group of patrons rush to restrain the chair man.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Outta here"]()
        return

    def tiddler73(self):
        self.text += """You hear Rachel's phone buzz. She pulls it from her pocket and reads a message.\n\n&quot;It's from a friend I saw at the bar,&quot; she reveals. &quot;The guy who went crazy... turns out his card said 'shot through the heart by Bon Jovi.'&quot; """
        if self.params['toldRachel'] == 1:
            self.text += """She looks at you. “How crazy a coincidence is that?”"""
        self.text += """\n\nYou pull up outside Rachel's villa. She sighs. &quot;I need some air and gonna go walk down the beach. Want to come along?&quot; she asks.\n\n\n\n"""
        self.current_links += ['Thanks', 'No thanks']
        self.actions += ['&quot;I could do with some air.&quot;', "&quot;I'd rather just drive home.&quot;"]
        return

    def tiddler74(self):
        self.text += """You try to make your way up the stairs, but it seems the current condition of your body isn't up to it. You'll have to stick to low-level tasks.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

    def tiddler75(self):
        self.text += """Look up? Ha! You're not falling for it that easily! Unfortunately, it turns out a billboard high above you DOES fall that easily, and straight onto you.\n\nAs the screams you hear around you slowly fade and your vision begins to blur, you look at the words which ended your life.\n\n&quot;Things are looking up!&quot;\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/center&gt;&lt;/html&gt;\n"""
        self.current_links += ['Later', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        self.params['meeting'] = 0
        self.params['timePassed'] = 0
        return

    def tiddler76(self):
        if self.params['inBedroom'] == 1 and self.params['seePoison'] == 1:
            self.params['returnVar'] = 1
        if self.params['manWait'] < 4 and self.params['returnVar'] <> 1:
            if self.params['lookedKitchen'] == 0:
                self.text += """You look around the room you're in and find it to be a small, modest kitchen."""
            if self.params['lookedKitchen'] == 1:
                self.text += """You're in a small, modest kitchen."""
            self.text += """ There's a sink with a kettle to its left, a collection of drawers to its right, and a cupboard below it. A pantry door stands tall in the corner, with a number of framed photograghs displayed on the wall next to it. A table sits at the centre of it all.\n\nStairs lead up and a door leads east. Another door leads back outside.\n\nThe axe remains stuck in the floor."""
            self.current_links += ['Drawers', 'Cupboard', 'Pantry', 'Photos', 'Table', 'Stairs', 'Bedroom', 'The door', 'Axe']
            self.actions += ['drawers', 'cupboard', 'pantry', 'framed photograghs', 'table', 'Stairs', 'east', 'outside', 'axe']
            self.params['lookedKitchen'] = 1
        if self.params['inBedroom'] == 1 and self.params['seePoison'] == 1 and self.params['manWait'] < 1:
            self.methodDict['Returns']()        
        return

    def tiddler77(self):
        self.text += """You move around to the side of the machine and read the slip of paper:\n\n"""
        if self.params['lookingUpPlayed'] == 1:
            self.text += """LOOKING UP\n"""
            self.current_links += ['LOOKING UP']
            self.actions += ['LOOKING UP']
        if self.params['lookingUpPlayed'] == 0:
            self.text += """XXXXXXXXXX\n"""
        if self.params['oldAgePlayed'] == 1:
            self.text += """OLD AGE\n"""
            self.current_links += ['OLD AGE']
            self.actions += ['OLD AGE']
        if self.params['oldAgePlayed'] == 0:
            self.text += """XXXXXXXXXX\n"""
        if self.params['joviPlayed'] == 1:
            self.text += """SHOT THROUGH THE HEART BY BON JOVI\n"""
            self.current_links += ['SHOT THROUGH THE HEART BY BON JOVI']
            self.actions += ['SHOT THROUGH THE HEART BY BON JOVI']
        if self.params['joviPlayed'] == 0:
            self.text += """XXXXXXXXXX\n"""
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler78(self):
        self.text += """&quot;Are you sure?&quot; she asks, raising a concerned eyebrow. &quot;What about your hands?&quot; You look down and realise they're shaking.\n\n\n\n"""
        self.current_links += ['On the beach', 'Drive off']
        self.actions += ["&quot;Maybe you're right.\xe2\x80\x9d", "&quot;I'll be fine.\xe2\x80\x9d"]
        return

    def tiddler79(self):
        self.text += """David is, as usual, trying to conceal the fact that he's rapidly approaching forty by wearing clothes that belong on a twenty-five year old body. He has styled his hair into a faux hawk despite his obvious receding hairline.\n\nHe really does seem all a little too pathetic, but then you remember the infuriating fact that he's your boss.\n\n"""
        if self.params['meeting'] == 1:
            self.methodDict['Meeting 1']()
        if self.params['meeting'] == 2:
            self.methodDict['Meeting 2']()
        if self.params['meeting'] == 1:
            self.params['meeting'] = 2
        if self.params['meeting'] <= 2:
            self.current_links += ['Logo', 'Co-workers']
            self.actions += ['Look at company logo.', 'Look at your co-workers.']
        return

    def tiddler80(self):
        self.text += """phone is in another building, can ask why he says because ne doesnt like people calling him.\n\n&quot;she's gone now. they're all gone. and soon, you'll be gone too.&quot;\n\nlimted time after certain actions are performed.\n\nmake situation where you're acught snooping, he confronts you and you have to come up with excuses. (i was looking for something warm), he replies snarkily and tells you to get out.\n\nif you dont take bullets and you poison him, he kills you before he dies\n\nafter a few talks he says &quot;sorry im not too talkative. been a while since i had company. i'm a little rusty.&quot;\n\nif you talk to him more than two times, you get the good ending of him asking about you when help arrives, and him saying that he might start going out and talking to people again\n\nask why he has gun, tell you he wasnt sure about you, becomes ashamed\n\nwhy dont you have a phone &quot;because  id ont like company&quot; he says giving you a cold stare.\n\nif you stay in car, it turns into a survival game\n\nheat can with cigarette lighter, make blanket out of something"""
        self.current_links += []
        self.actions += []
        return

    def tiddler81(self):
        self.text += """Rachel begins to ascend the stairs. &quot;I'm running a little late, sorry! Give me another couple minutes. Bon Jovi will keep you company.&quot;\n\nYour eye twitches involuntarily. If The Machine is to be believed, the song Shot Through the Heart by American rock band Bon Jovi will signify your death. And The Machine is always to be believed.\n\n&quot;Here he comes!&quot; Rachel yells from the second floor. You look towards the bottom of the stairs and see a small, ginger Pomeranian waddle down them and towards you.\n\n&quot;Hello,&quot; the furry creature says as he looks up at you. &quot;I'm Bon Jovi!&quot;\n\n\n\n\n\n\n"""
        self.current_links += ['Crazy', 'Doggy with a gun', 'Sing a song', 'Shoo', 'Excused']
        self.actions += ['&quot;I must be going crazy.&quot;', "&quot;You don't happen to know how to use a gun, do you?&quot;", '&quot;Erm, hello. Care to sing one of your classics?&quot;', '&quot;Shoo. Go away.&quot;', '&quot;Excuse me.&quot;']
        return

    def tiddler82(self):
        self.text += """You begin to run across the street and get out your phone. Sadly, you're so distracted with looking up the number that you don't notice the large truck speeding down the street.\n\nYou were supposed to be a smash hit at the """
        if self.params['fired'] == 0:
            self.text += """meeting"""
        if self.params['fired'] == 1:
            self.text += """interview"""
        self.text += """, not on the road!\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/center&gt;&lt;/html&gt;\n\n"""
        self.current_links += ['Later', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        self.params['meeting'] = 0
        self.params['timePassed'] = 0
        return

    def tiddler83(self):
        if self.params['ignition'] == 0:
            self.text += """You push the airbag out of the way and see if the car will start.\n\nIt doesn't."""
        if self.params['ignition'] == 1:
            self.text += """You try the ignition again to see if the car has suddenly decided that it wants to start.\n\nIt hasn't."""
        self.current_links += ['Wait', 'Phone', 'Ignition', 'Outside']
        self.actions += ['Wait.', 'Try using your mobile phone.', 'Try starting the car again.', 'Go outside.']
        if self.params['ignition'] == 0:
            self.params['ignition'] = 1
        return

    def tiddler84(self):
        self.text += """You attempt to pull the axe from the wooden floor, but it's wedged in there good and proper, not to mention that you're not exactly at optimal strength.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

    def tiddler85(self):
        self.text += """You decide to play it cool, and ignore your potential assailant.\n\nYou notice everyone else is also ignoring him, which is a bit odd considering his level of fame. You look over to him again and realise it's only a cardboard standee.\n\nStandees don't have much of a history of gun violence, so you relax. You look around and see Rachel beckoning over to her.\n\nDespite your efforts to hide your initial concern, it seems it didn't work quite well enough. &quot;Are you okay?&quot; Rachel asks with a concerned raised eyebrow.\n\n\n\n"""
        self.current_links += ['Reveal to Rachel', 'Sit on it']
        self.actions += ['Tell her about your death.', 'Say no and sit down at a table with her.']
        return

    def tiddler86(self):
        self.text += """There's still a bus to catch!\n\nAll the commotion has held up the traffic, but it won't last. You could try to run down the street and catch up to the bus while it's stalled, or run down the alley to meet with the bus on the next street, though there is the risk of a loading truck blocking your path.\n\nAnother thought occurs. You could dash down to a main street while looking up the number of a taxi company in your phone, and arrange for someone to drive you to the building."""
        self.params['timePassed'] = self.params['timePassed'] + 1
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """\n\nYou have """ + str(self.params['timeToGo']) + """ minutes left!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!\n\n\n\n\n"""
        self.current_links += ['Up your alley', "Ain't worth it", 'Hell cab']
        self.actions += ['Go down the alley and try to meet the bus at the next street. Fifty-fifty chance of success. (Gain two minutes on success. Lose three on failure)', 'Just run down the street! (Two minutes)', 'Call a cab. (One minute)']
        return

    def tiddler87(self):
        self.text += """Peak hour ended an hour or so ago, alleviating the feeling of being a tinned sardine that’s commonly associated with shopping malls, though there are still quite a few people busily bumbling about.\n\nTo your left is a fast food restaurant. To the right is a UFO catcher, and a poster is hanging on the wall beside it. Behind you is the one of the mall's exits.\n\nIn front of you stands the Machine.\n\n"""
        if self.params['coins'] > 0:
            self.text += """You're carrying """ + str(self.params['coins']) + """ dollars in change."""
        if self.params['coins'] == 0:
            self.text += """You've spent all the loose change you were carrying."""
        self.current_links += ['Restaurant', 'UFO Catcher', 'Poster', 'Exit', 'The Machine']
        self.actions += ['fast food restaurant', 'UFO catcher', 'poster', "mall's exits", 'the Machine']
        return

    def tiddler88(self):
        self.text += """&quot;Brilliant,&quot; proclaims one yes man sitting at the table. &quot;Genius,&quot; says another. &quot;Groin grabbingly great,&quot; yells one who is clearly a little too excited.\n\n&quot;Yes,&quot; David booms. &quot;I hope it's not arrogant of me to say that I am the greatest man in the world.&quot;\n\nUneasy laughter breaks out from around the table, no one quite sure if David seriously believed this or not.\n\n&quot;We'll have this slogan plastered on buses and billboards across the city within the month! Any questions? Good. Meeting adjourned!&quot;\n\n\n\n"""
        self.current_links += ['Leave meeting', 'Reveal']
        self.actions += ['Leave with everyone else.', 'Reveal your death card to David.']
        return

    def tiddler89(self):
        self.text += """You're still not sure how you ended up with one of the higher PR positions. The only reason you’re at the company at all is with the insistence and aid of your friend, Hannah, who now runs one of the larger branches in another city.\n\nDavid is always saying how you should look up to her for inspiration.\n\n&quot;As I was saying, I was unsatisfied with the idiots at the advertising company we were working with, so we bought it and fired everyone,&quot; David proclaims with pride."""
        self.current_links += []
        self.actions += []
        return

    def tiddler90(self):
        self.text += """You insert your finger, wince slightly at the jab, then pick up and read the card that’s quickly spat out.\n\n&lt;html&gt;&lt;h1&gt;&lt;center&gt;LOOKING UP&lt;/center&gt;&lt;/h1&gt;\n&lt;html&gt;&lt;h4&gt;&lt;center&gt;YEARS LATER...&lt;/center&gt;&lt;/h4&gt;&lt;/html&gt;\nOh, crap! Crap, crap, crap! Crappity crappy crap!\n\nPoop.\n\nYou're late for work for the third time this month! Your boss, David, is going to be steamed!\n\nYou dash out of the elevator and head straight for the meeting room, only to be blocked by a gaggle of co-workers who don't seem to appreciate the gravity of your situation. Between the crowd is Sarah's desk, which she is just about to sit at."""
        self.params['lookingUp'] = 1
        self.params['lookingUpPlayed'] = 1
        self.current_links += ['Leap', 'Dive', 'Calm']
        self.actions += ["Dramatically leap over Sarah's desk.", "Dramatically dive under Sarah's desk.", "Calmly move through the crowd and around Sarah's desk."]
        self.params['meeting'] = 0
        self.params['fired'] = 0
        self.params['timePassed'] = 0
        self.params['busRandom'] = 0
        return

    def tiddler91(self):
        self.text += """You insert your finger, wince slightly at the jab, then pick up and read the card that’s quickly spat out.\n\n&lt;html&gt;&lt;h1&gt;&lt;center&gt;OLD AGE&lt;/center&gt;&lt;/h1&gt;\n&lt;html&gt;&lt;h4&gt;&lt;center&gt;YEARS LATER...&lt;/center&gt;&lt;/h4&gt;&lt;/html&gt;\nIt was getting harder to see through the flurry of snow, so much so that you were considering maybe, just maybe, it wasn't such a great idea to go out driving during the worst snowstorm the region has had in over forty years. \n\nBut hey, you have a schedule to keep, and it's not like anything bad could happen to you. You continue to plow down the road to the best of your ability.\n\nSuddenly, a deer appears in your headlights!"""
        self.params['oldAge'] = 1
        self.params['oldAgePlayed'] = 1
        self.params['phone'] = 0
        self.params['carWait'] = 0
        self.params['car'] = 0
        self.params['ignition'] = 0
        self.params['wentOut'] = 0
        self.params['lost'] = 0
        self.params['axeAsk'] = 0
        self.params['seePoison'] = 0
        self.params['getPoison'] = 0
        self.params['poisonCount'] = 0
        self.params['poisoned'] = 0
        self.params['inBedroom'] = 0
        self.params['manWait'] = 0
        self.params['lookCloth'] = 0
        self.params['lookedKitchen'] = 0
        self.params['getBullets'] = 0
        self.params['waitingForHelp'] = 0
        self.params['sarah'] = 0
        self.params['askLooking'] = 0
        self.current_links += ['BREAK', 'SWERVE', "YOU'RE A TERRIBLE PERSON"]
        self.actions += ['Slam on your brakes!', 'Swerve out of the way!', 'Screw the deer! Keep on driving!']
        return

    def tiddler92(self):
        self.text += """You take the poison and hide it under your jacket.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['getPoison'] = 1
        self.methodDict["Kitchen"]()
        return

    def tiddler93(self):
        if self.params['manWait'] == 0:
            self.text += """You're in a small, musky bedroom. A large double bed covered with a thick blanket is at the end of the room. Next to it is small nightstand with a lamp and photograph placed on top of it.\n\nA closet is against one wall, with a small table next to it housing a couple wigs. Along the opposite wall is a set of drawers. Above it sits a painting.\n\nThe door to the kitchen is to the west."""
            self.current_links += ['Photo', 'Closet', 'Wigs', 'Bedroom drawers', 'Painting', 'Kitchen']
            self.actions += ['photograph', 'closet', 'wigs', 'drawers', 'painting', 'west']
            self.params['inBedroom'] = 1
        if self.params['manWait'] > 0:
            self.text += """It's probably not a good idea to go poking around the bedroom while John is in there.\n\n"""
            self.methodDict['Returns']()
        return

    def tiddler94(self):
        self.text += """Hulk Handsome"""
        self.current_links += []
        self.actions += []
        return

    def tiddler95(self):
        self.text += """&quot;Cool,&quot; she says, nodding in approval. &quot;It's how I kill time on my lunch break.&quot; She munches on a turkey sandwich.\n\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Another"]()
        return

    def tiddler96(self):
        self.text += """&quot;Of course.&quot;\n\n\n\n"""
        self.current_links += ['Why', 'Her']
        self.actions += ['&quot;Why do you deathspot?&quot;', '&quot;What did your card say?&quot;']
        return

    def tiddler97(self):
        self.text += """You swerve to avoid the deer, sending your car spinning off the icy roads and straight into a mound of snow with a mighty &quot;VOOMPF!&quot;\n\nLuckily, your head safely hits the quickly inflated airbag and no part of you seems to be seriously injured. Except for maybe your pride.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Inside car"]()
        return

    def tiddler98(self):
        self.text += """She rolls her eyes. &quot;That's not very fun,&quot; she begins. &quot;And also very unoriginal. Be imaginative!&quot; She jams some more turkey in her mouth while pointing at someone else approaching the Machine. &quot;Here's another one.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Yet another"]()
        return

    def tiddler99(self):
        self.text += """She finishes eating her lunch before giving an answer. &quot;Turkey sandwich.&quot; She looks at her watch. &quot;I'm gonna be late. Maybe I'll see you around.&quot; She gives a gentle smile and a weak wave before disappearing among the crowd of people.\n\n\n\n"""
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        self.params['chatted'] = 1
        return

    def tiddler100(self):
        self.text += """&quot;Heh, sure you're not,&quot; she says, shooting a knowing look in your direction. &quot;It's how I kill time on my lunch break.&quot; She munches on a turkey sandwich.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Another"]()
        return

    def tiddler101(self):
        self.text += """make the bar fight some kind of boardgame, like SWAHSBUCKLER or ROBORALLY\n\nit seems fights happen in this bar often, because the bottles are made from plastic, but it's still enough to give a good thump and stun you"""
        self.current_links += []
        self.actions += []
        return

    def tiddler102(self):
        self.text += """&lt;html&gt;&lt;center&gt;&lt;h1&gt;MACHINE OF DEATH&lt;/h1&gt;\n\n&lt;i&gt;Three short stories written and designed by Hulk Handsome. Based on the Machine of Death concept by Ryan North, used with permission. For more information, visit &lt;a href=&quot;http://machineofdeath.net&quot;&gt;machineofdeath.net&lt;/a&gt;.&lt;/i&gt;&lt;/center&gt;&lt;/html&gt;\nYou check the contents of your shopping basket: bread, milk and alcohol. Well, that's all the essentials, so you pay for your items, and head back out into the mall. \n\nOn your way to one of the exits, the clinking of change bouncing around your pocket distracts you. Perhaps you should treat yourself to something? You stop walking and take a look around. \n\n"""
        self.params['coins'] = 5
        self.params['win'] = 0
        self.params['poop'] = 0
        self.params['chatted'] = 0
        self.params['machine'] = 0
        self.params['busRandom'] = 0
        self.current_links += []
        self.actions += []
        self.methodDict["Standing in a mall"]()
        return

    def tiddler103(self):
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!"""
        self.text += """\n\nRight, now for some face time! \n\n\n\n"""
        self.current_links += ['Winning smile', 'Losing smile']
        self.actions += ["Give your teeth a good brushin'. (Two minutes)", "You're already funky fresh! Just apply a little touch up. (One minute)"]
        return

    def tiddler104(self):
        self.text += """You pop open the bottle of poison and pour some in his drink. Hopefully not enough that he will detect it, but still a sufficient amount to have an effect.\n\n"""
        self.params['poisoned'] = 1
        self.current_links += []
        self.actions += []
        self.methodDict["Returns"]()
        return

    def tiddler105(self):
        self.params['lookingUpPlayed'] = 0
        self.params['oldAgePlayed'] = 0
        self.params['joviPlayed'] = 0
        self.params['lookingUp'] = 0
        self.params['oldAge'] = 0
        self.params['jovi'] = 0
        self.params['firstDeathGiven'] = 0
        self.current_links += []
        self.actions += []
        self.methodDict["The beginning"]()
        return

    def tiddler106(self):
        if self.params['manWait'] == 3:
            self.methodDict['One on one']()
        self.params['returnVar'] = 0
        self.params['inBedroom'] = 0
        if self.params['manWait'] == 0:
            self.text += """John  returns from outside. He shakes off the snow gathered on him and turns on the kettle. He turns back around to look at you.\n\n&quot;They said they'll be ‘ere in about fifteen minutes, so just sit tight,&quot; he says moments before the water stops boiling. He gets out two mugs and places a tea bag in each. He places one on the table and hands the other to you.\n\n&quot;I'll be back in a minute.&quot; He goes into the bedroom and closes the door behind him.&lt;html&gt;&lt;/p&gt;&lt;/html&gt;"""
        if self.params['manWait'] == 1:
            self.text += """You hear John rummaging around in the next room.&lt;html&gt;&lt;/p&gt;&lt;/html&gt;"""
        if self.params['manWait'] == 2:
            self.text += """You hear a few things fall to the floor in the next room, followed by John grumbling, &quot;Where the hell are they?&quot;&lt;html&gt;&lt;/p&gt;&lt;/html&gt;"""
        if self.params['manWait'] < 3:
            self.params['manWait'] = self.params['manWait'] + 1
            self.current_links += ['Waiting in the kitchen', 'Drink tea']
            self.actions += ['Wait.', 'Drink tea.']
            if self.params['getPoison'] == 1 and self.params['poisoned'] == 0:
                self.current_links += ['Poison']
                self.actions += ['Poison his drink.']
        return

    def tiddler107(self):
        self.text += """You turn around and look at the two sliding doors leading to the outside world.\n\n\n"""
        self.current_links += ['Leave', 'Standing in a mall']
        self.actions += ['You decide to leave.', 'You decide to stay and turn back around.']
        return

    def tiddler108(self):
        self.text += """You enter the meeting room with a combination of urgency and nonchalance, a fusion that would be entirely impossible under any other circumstances. Your boss, David, stands at the other end of the room. He sends enough daggers your way to supply an assassins' guild for life.\n\nYou sit at the table with your co-workers and try to pay attention to the meeting.\n\n\n\n\n"""
        self.current_links += ['Logo', 'Co-workers', 'David']
        self.actions += ['Look at company logo.', 'Look at your co-workers.', 'Look at David.']
        self.params['meeting'] = 1
        return

    def tiddler109(self):
        self.text += """&quot;I'm a lover, not a fighter!&quot; the pooch proudly proclaims, with a hint of indignation. &quot;I wouldn't even know what to do with a gun if I found one.&quot;"""
        if self.params['waitForRach'] == 3:
            self.text += """&lt;html&gt;&lt;/p&gt;&lt;/html&gt;Both you and Bon Jovi become distracted by Rachel bounding down the stairs with her usual energy."""
        self.params['saidGun'] = 1
        if self.params['waitForReach'] <> 3:
            if self.params['saidCrazy'] == 0:
                self.current_links += ['Crazy']
                self.actions += ['&quot;I must be going crazy.&quot;']
            if self.params['saidSing'] == 0:
                self.current_links += ['Sing a song']
                self.actions += ['&quot;Care to sing one of your classics?&quot;']
            if self.params['saidExcused'] == 0:
                self.current_links += ['Excused']
                self.actions += ['&quot;Excuse me.&quot;']
            self.current_links += ['Shoo']
            self.actions += ['&quot;Shoo.&quot;']
            self.params['waitForRach'] = self.params['waitForRach'] + 1
        return

    def tiddler110(self):
        self.text += """You scream and jump and make one hell of a spectacle of yourself.\n\nAstonishingly, it seems to have paid off. The bus comes to a halt at the end of the street, allowing you to catch up and climb aboard. You sit impatiently, watching various buildings go by until it reaches your stop. You hop out and enter the building.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Something foyer"]()
        return

    def tiddler111(self):
        self.text += """You rummage through the cupboard under the sink and find what one would expect to find there. A scrubbing brush, a few dirty rags, and so on. """
        if self.params['getPoison'] == 0:
            self.text += """Then you see a bottle of drain cleaner with a very big poison warning on it."""
            self.params['seePoison'] = 1
        self.current_links += ['Kitchen']
        self.actions += ['Return your attention to the kitchen.']
        if self.params['getPoison'] == 0:
            self.current_links += ['Snatched']
            self.actions += ['Take poison.']
        return

    def tiddler112(self):
        self.text += """Your attempt to dive under Sarah's desk fails quite spectacularly, resulting in you smashing your noggin on the edge. You stand up and rest a palm on your throbbing skull.\n\n&quot;Sorry, Sarah.&quot;\n\n&quot;It's fine,&quot; she replies, trying to contain her laughter as she sits at her desk. &quot;Just get to the meeting.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Meeting"]()
        return

    def tiddler113(self):
        self.text += """Ah, sweet relief! You take care of business then march into the appointed room to take care of another kind of business.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.params['didPee'] = 1
        self.methodDict["Showtime!"]()
        return

    def tiddler114(self):
        self.text += """You opt out of a full shower, and instead settle for a quick rinse around the essential areas. Deodorant takes care of the rest. Or rather, you hope it will.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 4
        self.params['showered'] = 0
        self.methodDict["Teeth"]()
        return

    def tiddler115(self):
        if self.params['phone'] == 0:
            self.text += """Much to your lack of surprise, it appears that the combination of location and weather is getting in the way of phone reception.\n\nYou consider playing a round of Irate Fowls but decide it's probably best to conserve battery power."""
        if self.params['phone'] == 1:
            self.text += """You check your phone again to see if the reception situation has changed. \n\nIt hasn't."""
        self.current_links += ['Wait', 'Ignition', 'Outside']
        self.actions += ['Wait.', 'Try starting the car.', 'Go outside.']
        self.params['phone'] = 1
        return

    def tiddler116(self):
        self.text += """You plump yourself on one of the barstools and give yourself a spin.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["The meeting"]()
        return

    def tiddler117(self):
        if self.params['win'] == 0:
            self.text += """You wander over to the UFO catcher and peek at what's trapped behind the glass. There doesn't seem to be anything too excit... holy hell! There's a Wee Rex Adorable Plush in there! It looks delightfully cuddly in all it's green glory."""
        if self.params['win'] == 1:
            self.text += """You've already won that delightful dinosaur! There's nothing else of interest in the UFO catcher."""
        if self.params['coins'] == 0 and self.params['win'] == 0:
            self.text += """&lt;html&gt;&lt;/p&gt;&lt;/html&gt;Sadly, you have no any remaining change to try to win this dazzling dinosaur."""
        if self.params['coins'] > 0 and self.params['win'] == 0:
            self.current_links += ['Play to win']
            self.actions += ['Jam in a coin and try to win that baby!']
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler118(self):
        self.text += """A Pie Floater. An inverted meat pie floating in mushy pea soup, drenched with tomato sauce. These are traditionally sold in vans in the streets of Australian cities, recommended to be eaten whilst standing, and also very, very drunk.\n"""
        if self.params['coins'] < 4:
            self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;Tragically (or perhaps luckily), you're not carrying enough money to experience this culinary curiosity."""
        if self.params['coins'] >= 4:
            self.current_links += ['Eating a floater']
            self.actions += ['Buy one for four dollars.']
        self.current_links += ['Menu']
        self.actions += ['See what else is on offer.']
        return

    def tiddler119(self):
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.text += """You sprint after the bus and... """
        if self.params['timePassed'] < 25:
            self.text += """catch up with it! You hop on, and it eventually drops you outside the office.\n\n"""
            self.methodDict['Something foyer']()
        else:
            self.text += """fail to catch up with it!\n\nYou could dash down to a main street while looking up the number of a taxi company in your phone, and arrange for someone to drive you to the building. Or just forget about it and move on with your life.\n\n"""
            self.params['timeToGo'] = 30 - self.params['timeToGo']
            if self.params['timeToGo'] > 0:
                self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
            if self.params['timeToGo'] == 0:
                self.text += """You're about to be late!"""
            if self.params['timeToGo'] < 0:
                self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!"""
            self.current_links += ['Hell cab', 'Gone home']
            self.actions += ['Call a cab. (One minute)', 'Call it quits.']
        return

    def tiddler120(self):
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!"""
        self.text += """\n\nAs your feet land on the pavement outside, a terrifying realisation occurs: you forgot to eat anything! You glance down the street and see a Tufo Dog stand.\n\n\n\n"""
        self.current_links += ['Eat eat eat', 'That song was terrible']
        self.actions += ['Better than being starving! (Two to three minutes)', 'Nothing gonna stop my stride! I gotta keep on moving! (One minute)']
        return

    def tiddler121(self):
        self.text += """She snorts and begins to laugh. She hunches over, as if she's struggling to breathe for a moment before coughing up some of her sandwich.\n\n&quot;You almost killed me with that joke,&quot; she says, a smile on her face. &quot;Would have almost been worth it. Let's see what we can come up for this one!&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.params['poop'] = 1
        self.methodDict["Yet another"]()
        return

    def tiddler122(self):
        self.text += """&quot;He's a cutie, isn't he?&quot; she says as she leans down and pets Bon Jovi. &quot;I'm dogsitting him for my friend. She was supposed to come with us tonight.&quot; A sudden realisation hits her. &quot;Oh, my friends bailed,&quot; she reveals. &quot;But it's okay, we'll either make new friends there or have fun on our own!&quot;\n\n&quot;Time to go!&quot; Rachel announces as she grabs your arm and pulls you outside, where the two of you get in your car.\n\n&quot;You like karaoke, right?&quot; she asks, as you begin to drive to the address she gave you. \n\n\n\n"""
        self.current_links += ['Sure do', 'Not at all']
        self.actions += ['&quot;Oh my Lordy wordy, yes.\xe2\x80\x9d', '&quot;Erm, not really.\xe2\x80\x9d']
        return

    def tiddler123(self):
        self.text += """The card reads &quot;POISONED.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Bedroom"]()
        return

    def tiddler124(self):
        self.params['toldRachel'] = 1
        self.text += """Her eyes widen as you reveal your fate to her. &quot;Why didn't you tell me this earlier?&quot; she exclaims. &quot;This is the worst place for you to be! Almost all of Bon Jovi’s songs are up for singing here! Come on, we'll go somewhere else.&quot;\n\nShe grabs your arm and pulls you towards the exit.\n\nAs you walk by the standee, you both stop in your tracks as a familiar melody flows from the speakers, and turn to the stage to see a middle-aged businessman begin to belt out the most terrifying words you could ever hear.\n\n&quot;Shot... through the heart... it's all part... of the game that we call love!&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Not over until the chiselled rocker sings"]()
        return

    def tiddler125(self):
        self.text += """You pick a sofa from the wide selection and plump yourself down on it. It feels like real leather.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["The meeting"]()
        return

    def tiddler126(self):
        self.text += """Are you happy? Is this what you want to do? If you didn't avoid that sign, would you be satisfied with how your life had turned out?\n\nSure, you're good at your job and it pays well, but is that all you want from work? \n\nIf not, maybe it's time for a change.\n\n\n\n"""
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.params['reflected'] = 1
        self.current_links += ['Gone home', 'Run, run']
        self.actions += ["Screw it. I'm going to find a new life right now. It's not going to be easy, but it's what I want.", "Maybe one day. But I'm satisfied right now, and I have bills to pay. Keep on going. (One minute)"]
        return

    def tiddler127(self):
        self.text += """&quot;How the hell was I supposed to know that would happen?&quot; she protests. &quot;I said I was sorry!&quot; She angrily stares out the window. “Don’t you think I feel awful enough as it is?”\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["A message"]()
        return

    def tiddler128(self):
        self.text += """You carefully consume the tofu dog, ensuring nothing drips onto you, and so that you can savour that sweet, sweet tastelessness.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['timePassed'] = self.params['timePassed'] + 3
        self.params['cleanEat'] = 1
        self.methodDict["Busted"]()
        return

    def tiddler129(self):
        if self.params['poisoned'] == 1:
            self.params['poisonCount'] = self.params['poisonCount'] + 1
        self.params['waitingForHelp'] = self.params['waitingForHelp'] + 1
        if self.params['waitingForHelp'] <> 5:
            if self.params['poisonCount'] <> 4:
                self.current_links += ['Killing time', 'Drink up']
                self.actions += ['Wait.', 'Drink tea.']
                if self.params['askLooking'] == 0:
                    self.current_links += ['Looking']
                    self.actions += ['Ask what he was looking for.']
                if self.params['sarah'] == 0:
                    self.current_links += ['Blood']
                    self.actions += ['Ask about the blood stains.']
                if self.params['sarah'] == 1:
                    self.current_links += ['Sarah']
                    self.actions += ['Ask about Sarah.']
                if self.params['sarah'] == 2:
                    self.current_links += ['Life after Sarah']
                    self.actions += ['Ask more about Sarah.']
        if self.params['poisonCount'] == 4:
            self.methodDict['What a rotten way to die']()
        if self.params['waitingForHelp'] == 5:
            self.methodDict['Rescue']()
        return

    def tiddler130(self):
        self.text += """Rachel hops into the passenger seat and immediately notices the gun. &quot;What the hell is that?&quot; she asks, her voice laced with fear. Before you can even explain, she gets out of the car. &quot;Stay the hell away from me!&quot; she blurts as she disappears into the crowd emerging from the bar.\n\nYou begin the long drive home. To break the silence, you turn the radio on.\n\n&quot;Shot... through the heart... it's all part... of the game that we call love!&quot;\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler131(self):
        self.text += """You take the gun out of your glove box and, to feel like an action hero, stuff it down the back of your pants, sliding your top over it to hide it from vision.\n\n"""
        self.current_links += []
        self.actions += []
        self.params['gun'] = 1
        self.methodDict["Bar"]()
        return

    def tiddler132(self):
        self.text += """You feel someone grab your arm, and look over to see that it’s Rachel. &quot;Let's get out of here,&quot; she says while motioning towards the exit.\n\nYou charge out of the bar and leap back into your car, adrenaline still pumping through your veins. As you slam the door, the glove box pops open and reveals your gun.\n\n\n\n"""
        self.current_links += ['See no evil', 'Nothing to hide']
        self.actions += ['Grab it and hide it in your jacket before Rachel can see it.', 'Leave it.']
        return

    def tiddler133(self):
        self.text += """Rachel hops into the passenger seat and buckles up. \n\nRachel is the first to break the brief silence as you drive back to her villa. &quot;That was crazy,&quot; she begins. &quot;I'm so sorry.&quot;\n\n\n\n"""
        self.current_links += ["Couldn't have known", 'Gotten me killed']
        self.actions += ["&quot;You couldn't have known that would happen.&quot;", '&quot;You could have gotten me killed!&quot;']
        return

    def tiddler134(self):
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!"""
        if self.params['timePassed'] <= 10:
            self.text += """\nSuddenly, a bus rockets past with a &quot;Things are looking up!&quot; poster plastered on its side. Normally this would make you grimace, but instead you're more concerned by the fact that it's the bus you're supposed to be catching."""
        if self.params['timePassed'] > 10:
            self.text += """You look down the street and notice a bus with a &quot;Things are looking up!&quot; poster plastered on its side. Normally this would make you grimace, but instead you're more concerned by the fact that it's the bus you're supposed to be catching.\n\n\n\n"""
        self.current_links += ['Gotta go fast!', 'Yell']
        self.actions += ['Try to catch up! (One minute)', "Try to gain the driver's attention with a mighty yell. There is one in a fifty chance it will work, but it would take you straight to the office! (Two minutes if failed)"]
        return

    def tiddler135(self):
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.text += """You look up, and see a large billboard rapidly approaching the ground. This is alarming as it's heading for the area you're currently occupying. You quickly dive out of the way, the sign just barely nicking your foot.\n\nYou get back up and look at the billboard. &quot;Things are looking up!&quot; it happily proclaims. \n\nYou really hate that slogan.\n\n"""
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left after this debacle!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!\n\n\n\n"""
        self.current_links += ['Reflection', 'Run, run']
        self.actions += ['Take a moment to reflect on your life after this near-death experience. (Two minutes)', "There's still a bus to catch! Keep on running! (One minute)"]
        return

    def tiddler136(self):
        self.text += """You wait.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Returns"]()
        return

    def tiddler137(self):
        self.text += """"""
        self.current_links += []
        self.actions += []
        self.methodDict["Look out below"]()
        return

    def tiddler138(self):
        self.text += """It's a traditional oil painting of white horse with a golden mane. It looks like the work of an amateur.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Bedroom"]()
        return

    def tiddler139(self):
        self.text += """She shrugs, saying &quot;Suit yourself.&quot; She finishes off her sandwich and walks away, disappearing into the crowd.\n\n"""
        self.params['chatted'] = 1
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your gaze to the mall']
        return

    def tiddler140(self):
        self.text += """You stride into the foyer, only for your swagger to stagger when you suddenly realise that you need to pee.\n\n"""
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!\n\n\n\n"""
        self.current_links += ['Pee freely', 'No pee for me!']
        self.actions += ['When you gotta go, you gotta go! (Two minutes)', 'No Time! Hold it in and get to the interview! (Zero minutes)']
        return

    def tiddler141(self):
        self.text += """&quot;Oh, I hope not,&quot; Bon Jovi says with a look of mild concern. &quot;Insanity isn't nearly as glamorous as the movies portray it. In fact, it's usually quite tragic for all involved.&quot; """
        if self.params['waitForRach'] == 3:
            self.text += """&lt;html&gt;&lt;/p&gt;&lt;/html&gt;Before you have time to finish this enlightening conversation, Rachel bounds down the stairs with her usual energy. """
        self.params['saidCrazy'] = 1
        if self.params['waitForReach'] <> 3:
            self.current_links += ['Still crazy']
            self.actions += ['&quot;How do you know that?&quot;']
            if self.params['saidGun'] == 0:
                self.current_links += ['Doggy with a gun']
                self.actions += ["&quot;You don't happen to know how to use a gun, do you?&quot;"]
            if self.params['saidSing'] == 0:
                self.current_links += ['Sing a song']
                self.actions += ['&quot;Care to sing one of your classics?&quot;']
            if self.params['saidExcused'] == 0:
                self.current_links += ['Excused']
                self.actions += ['&quot;Excuse me.&quot;']
            self.current_links += ['Shoo']
            self.actions += ['&quot;Shoo.&quot;']
            self.params['waitForRach'] = self.params['waitForRach'] + 1
        return

    def tiddler142(self):
        if self.params['lookCloth'] == 0:
            self.text += """You look down at the table, which has a thin, white cloth draped over it. You think you can see something on the table underneath it."""
        if self.params['lookCloth'] == 1:
            self.text += """You look down at the table, which has a thin, white cloth draped over it, hiding the blood stains underneath.\n\n\n\n"""
        self.current_links += ['Beneath', 'Kitchen']
        self.actions += ['Look under the cloth.', 'Turn your attention back to the kitchen.']
        return

    def tiddler143(self):
        self.text += """It does, however, stop at a red light further ahead.\n\n"""
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!\n\n\n\n"""
        self.current_links += ['Keep running', 'Cut off']
        self.actions += ['Sprint down the street and try to catch up with it at the light. (Two minutes)', 'You know the route! If you cut down the alley ahead, you can cut the bus off at the next street. Unfortunately, there is a fifty-fifty chance a truck will be loading and blocking the path. (Gain two minutes on success. Lose three on failure)']
        return

    def tiddler144(self):
        self.text += """You slam on the breaks, sending your car spinning off the icy roads and straight into a mound of snow with a mighty &quot;VOOMPF!&quot;\n\nLuckily, your head safely hits the quickly inflated airbag and no part of you seems to be seriously injured. Except for maybe your pride.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Inside car"]()
        return

    def tiddler145(self):
        self.text += """David continues his spiel. &quot;My first move as the CEO was to come up with an incredibly clever slogan for Albatross Airway’s new marketing campaign. And here it is...&quot;\n\nHe pulls a sheet from over a display, revealing a large piece of cardboard baring the words &quot;Things are looking up!&quot;\n\nYour eye twitches involuntarily.\n\n&quot;It has a double meaning,&quot; David begins, his voice laced with excitement. &quot;Not only is it informing our customers that the recession is over and that it's safe to spend money on travelling again, but to also look to our planes in the sky as an escape!&quot; He strikes what he must believe to be a heroic pose. &quot;Quite clever, I'm sure you'll agree.&quot;\n\nThe room bursts into applause and cheers.\n"""
        self.params['meeting'] = 3
        self.current_links += ['Continue meeting', 'Continue meeting', 'Continue meeting']
        self.actions += ['Applause with the crowd.', 'Tap your finger on the desk nervously.', 'Do nothing.']
        return

    def tiddler146(self):
        self.text += """&quot;I went crazy once,&quot; he admits with a hint of shame. &quot;I believed I was a Pomeranian.&quot;"""
        if self.params['waitForRach'] == 3:
            self.text += """&lt;html&gt;&lt;/p&gt;&lt;/html&gt;Before you have time to finish this enlightening conversation, Rachel bounds down the stairs with her usual energy.\n"""
        if self.params['waitForReach'] <> 3:
            self.current_links += ['The hard truth']
            self.actions += ['&quot;But you are a Pomeranian!&quot;']
            if self.params['saidGun'] == 0:
                self.current_links += ['Doggy with a gun']
                self.actions += ["&quot;You don't happen to know how to use a gun, do you?&quot;"]
            if self.params['saidSing'] == 0:
                self.current_links += ['Sing a song']
                self.actions += ['&quot;Care to sing one of your classics?&quot;']
            if self.params['saidExcused'] == 0:
                self.current_links += ['Excused']
                self.actions += ['&quot;Excuse me.&quot;']
            self.current_links += ['Shoo']
            self.actions += ['&quot;Shoo.&quot;']
            self.params['waitForRach'] = self.params['waitForRach'] + 1
        return

    def tiddler147(self):
        self.text += """You duck to the ground and hide behind a table! You then look over to Jon Bon Jovi and realise it's only a cardboard standee.\n\nRachel laughs. &quot;What are you doing? You haven't even had anything to drink yet!&quot;\n\n\n\n"""
        self.current_links += ['Reveal to Rachel', 'Sit on it']
        self.actions += ['Tell her about your death.', 'Apologise and sit down at a table with her.']
        return

    def tiddler148(self):
        self.text += """time-travel mishap, you see yourself die and try to stop it but destory universe, let it happen or go back and set it up to kill yourself. your friend sends you to try and save him, turns out he killed you? you go back in time and kill him before he kills you, send you in a loop because of paradox\n\nuse laser weapon in time travle story to avoid over using guns\n\nyou can refuse to fix the paradox and let the universe cease to exists, or kill guy at wrong time which sends everything backwards since it couldnt have happened, or you can choose to kill yourself\n\ndon't worry, i'm happy. we had a really good run, you and I.\nstraight to the point. you remind me of me when i was your age.\n\nhad did"""
        self.current_links += []
        self.actions += []
        return

    def tiddler149(self):
        self.text += """&quot;Great! Because that's exactly where we're going.&quot; A huge smile conquers her face. &quot;It's one of my favourite places in the world.”\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Outside the karaoke bar"]()
        return

    def tiddler150(self):
        self.text += """You scream and jump and make one hell of a spectacle of yourself.\n\nUnsurprisingly, it doesn't pay off. The bus continues on its merry way despite your self-humiliation.\n\n"""
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.current_links += []
        self.actions += []
        self.methodDict["Streets"]()
        return

    def tiddler151(self):
        self.text += """&quot;Yes, Sir,&quot; you reply. David nods. &quot;Good to know. Now, go do some work.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Later"]()
        return

    def tiddler152(self):
        self.text += """You sit silently at the table with your accidental companion. A strong wind beats against the walls outside.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Time to talk"]()
        return

    def tiddler153(self):
        self.text += """&lt;html&gt;&lt;center&gt;&lt;h1&gt;SO HOW DID YOU DO?&lt;/h1&gt;&lt;/html&gt;\n"""
        self.params['interviewScore'] = 0
        if self.params['showered'] == 1:
            self.text += """You showered, and blessed the room with a fruity aroma.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        else:
            self.text += """You didn't shower, and cursed the room with a pungent funk.\n"""
        if self.params['brushedTeeth'] == 1:
            self.text += """You brushed your teeth, and showed off your winning smile.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        else:
            self.text += """You didn't brush your teeth, and made the panel wince every time you smiled.\n"""
        if self.params['dressedWell'] == 1:
            self.text += """You dressed to impress, and impress you did.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        else:
            self.text += """The panel looked at your messy outfit with disapproving eyes.\n"""
        if self.params['ateFood'] == 1:
            self.text += """You ate some food and thus wasn't distracted by hunger.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        else:
            self.text += """You didn't eat food, and kept getting distracted by a rumbling stomach.\n"""
        if self.params['ateFood'] == 1:
            if self.params['cleanEat'] == 1:
                self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;&lt;html&gt;&lt;/br&gt;&lt;/html&gt;You took care while eating, making sure not to leave any unsightly stains for the panel to see.\n"""
                self.params['interviewScore'] = self.params['interviewScore'] + 1
            else:
                self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;&lt;html&gt;&lt;/br&gt;&lt;/html&gt;You didn't take care while eating, and can't help but wonder if the panel noticed the chutney stain.\n"""
        if self.params['reflected'] == 1:
            self.text += """You took time to reflect after your near-death experience, leaving you confident.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        else:
            self.text += """You didn't pause for reflection after your near-death experience, leaving you noticeably shaken.\n"""
        if self.params['didPee'] == 1:
            self.text += """You used the toilet, forbidding your bladder from distracting you.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        else:
            self.text += """You held your pee the entire time, causing you to squirm in your seat.\n"""
        if self.params['timePassed'] <= 30:
            self.text += """You weren't late! Punctuality is always impressive.\n"""
            self.params['interviewScore'] = self.params['interviewScore'] + 1
        if self.params['timePassed'] > 30:
            self.text += """You were late for the important date!\n"""
        if self.params['interviewScore'] >= 5:
            if self.params['fired'] == 0:
                self.text += """Despite the hiccups, you manage to impress the panel and return to your office with a signed contract. Congratulations!\n"""
            if self.params['fired'] == 1:
                self.text += """ Despite the hiccups, the interview ended with you getting offered a job. Congratulations!\n"""
        else:
            if self.params['fired'] == 0:
                self.text += """All these hiccups lead to one grand disaster. You leave the office without a signed contract, and soon you will be without a career. \n"""
            if self.params['fired'] == 1:
                self.text += """ All these hiccups lead to one grand disaster. You leave the office with no job and with no idea of what you’ll do now. \n"""
        self.text += """&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/center&gt;&lt;/html&gt;\n"""
        self.params['meeting'] = 0
        self.params['timePassed'] = 0
        self.current_links += ['Later', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler154(self):
        self.text += """You take a look at some of the menu "highlights."\n\n\n\n\n"""
        self.current_links += ['Lister', 'Floater', 'Sinner', 'AB', 'Standing in a mall']
        self.actions += ['A Lister sandwich.', 'A pie floater.', "A sinner's sandwich.", 'An A.B.', 'Return to the centre of the mall.']
        return

    def tiddler155(self):
        self.text += """It's like there's a party in your mouth and everyone's throwing up!\n\n"""
        self.params['coins'] = self.params['coins'] - 5
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler156(self):
        self.params['timeToGo'] = 30 - self.params['timePassed']
        if self.params['timeToGo'] > 0:
            self.text += """You have """ + str(self.params['timeToGo']) + """ minutes left!\n"""
        if self.params['timeToGo'] == 0:
            self.text += """You're about to be late!\n"""
        if self.params['timeToGo'] < 0:
            self.text += """You're now """ + str(self.params['timeToGo']) + """ minutes late!\n"""
        self.text += """Now to decide which garments you'll use to cover up your rude bits.\n\n\n\n"""
        self.current_links += ['Dress to impress', 'Floordrobe']
        self.actions += ['Look for and iron your best outfit. (Five minutes)', 'Throw on the first thing you find on the floor. (Three minutes)']
        return

    def tiddler157(self):
        self.text += """&quot;I swore I had some hot water bottles in there,&quot; he answers. &quot;Would 'ave been handy.&quot; He shrugs. &quot;I s’pose you'll have to make do with tea.&quot;\n\n"""
        self.params['askLooking'] = 1
        self.current_links += []
        self.actions += []
        self.methodDict["Time to talk"]()
        return

    def tiddler158(self):
        if self.params['wentOut'] == 0:
            self.text += """You bundle yourself up as much as you can and step out of the car. As suspected, it is cold. Very cold. Snow storms around you."""
        if self.params['wentOut'] == 1:
            self.text += """You head back out into the freezing cold."""
        self.params['wentOut'] = 1
        self.current_links += ['Inside car', 'Explore']
        self.actions += ['Get back in the car.', 'Go in search of help.']
        return

    def tiddler159(self):
        self.text += """&quot;Excuse me,&quot; you say with the utmost politeness as you gently carve your way through the congregation of co-workers.\n\n&quot;Good morning, Sarah,&quot; you say, while giving her a nod as she sits at her desk. &quot;Good morning,&quot; she replies. &quot;The meeting has already started. You better get a move on if you don't want David to bite your head off.&quot;\n\nYou ponder this thought and increase your pace after deciding that you like your head where it is, perched perfectly atop your neck.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Meeting"]()
        return

    def tiddler160(self):
        self.text += """&quot;Oh,&quot; she says as the smile leaves her face. &quot;Well, then you can get drunk while you listen to me sing! But if you get bored we'll go somewhere else.&quot; A smile returns. &quot;We'll have fun one way or another.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Outside the karaoke bar"]()
        return

    def tiddler161(self):
        self.text += """Not only do you give your teeth a good brushing, you also give your tongue a rub down, because that's what commercials say you have to do these days.\n\n"""
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.params['brushedTeeth'] = 1
        self.current_links += []
        self.actions += []
        self.methodDict["Dressing time"]()
        return

    def tiddler162(self):
        self.text += """You leap to your feet, adrenaline helping you ignore the pain surging through every inch of your body. You slam your entire weight as hard as you can against your potential assassin, knocking him backwards and prompting him to drop the axe, which falls blade first into the wooden planks of the floor with a thunk.\n\n&quot;What the hell are you doing here?&quot; You look at the source of the voice and get your first clear look at the axe wielder, and see that it's an elderly man, maybe in his early 70s, though looking surprisingly fit for his apparent age. He's standing behind a chair, both hands gripped tightly on the back as if he's prepared to use it as a weapon.\n\n\n\n"""
        self.current_links += ['Explain', 'Axe to grind']
        self.actions += ['Explain your situation.', 'Ask why the hell he had an axe.']
        return

    def tiddler163(self):
        self.text += """&quot;This isn't a dog and pony show!&quot; He pauses, perhaps for dramatic effect, and then bursts into song and dance. You recognise the tune as the early 90s hit, I'll Sleep When I'm Dead.\n\nHe yawns and lies down on the floor after his energetic performance. &quot;Actually, I'm getting pretty sleepy now.&quot;\n"""
        if self.params['waitForRach'] == 3:
            self.text += """&lt;html&gt;&lt;/p&gt;&lt;/html&gt;Both you and Bon Jovi become distracted by Rachel bounding down the stairs with her usual energy."""
        self.params['saidSing'] = 1
        if self.params['waitForReach'] <> 3:
            if self.params['saidCrazy'] == 0:
                self.current_links += ['Crazy']
                self.actions += ['&quot;I must be going crazy.&quot;']
            if self.params['saidGun'] == 0:
                self.current_links += ['Doggy with a gun']
                self.actions += ["&quot;You don't happen to know how to use a gun, do you?&quot;"]
            if self.params['saidExcused'] == 0:
                self.current_links += ['Excused']
                self.actions += ['&quot;Excuse me.&quot;']
            self.current_links += ['Shoo']
            self.actions += ['&quot;Shoo.&quot;']
            self.params['waitForRach'] = self.params['waitForRach'] + 1
        return

    def tiddler164(self):
        self.text += """She sighs. &quot;I'm really not that crazy. I mean, maybe when I was a bored teen with too much money. But now I just feel worn out.&quot; She stares at the sand.\n\n&quot;This was the first time I've been out in a while.&quot; She looks over to you. &quot;Maybe I felt I had to take you there because of my reputation. I mean, I still love the place and had so many good times there, but...&quot; she trails off and looks out towards the ocean.\n\n&quot;I'm going to go let Bonny have a run,&quot; she eventually says. """
        if self.params['toldRachel'] == 1:
            self.text += """You better be careful around him,&quot; she adds with a mischievous grin. """
        self.text += """&quot;We'll be right back.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["The choice"]()
        return

    def tiddler165(self):
        self.text += """The poster is advertising the upcoming tour of stand-up comedian Phil Bison, also known as the Cancer Comic.\n\nBefore the Machine hit, jokes about fatal illnesses were considered “edgy” and politically incorrect, often leading to controversy. Now they’re as common as knock, knock jokes.\n\nOf course, modern comedians only get away with it because of their slips. As his stage name suggests, Bison received one of the more straight forward machine results: CANCER. It doesn’t take a genius to figure out what themes he explores with his humour.\n\nSome are of the opinion that it’s healthy for people to laugh at their own tragedies, believing it’s a valuable coping mechanism. Others accuse it of being exploitive.\n\nIt doesn't help that there was once a comedian who &quot;faked his own death,&quot; claiming he was going to die from an HIV infection. At the height of his fame, he was constantly surrounded by people, something he seemed to treasure. When it was discovered he lied about his death, his career was instantly destroyed.\n\nHis slip actually said ISOLATION.\n\n\n"""
        self.current_links += ['Standing in a mall']
        self.actions += ['Return your eyes to the mall.']
        return

    def tiddler166(self):
        self.text += """Fuck nature! What has it ever done for you? You press your foot down on the accelerator and slam into the deer with a great thump.\n\nIf deer could laugh, it would have had the last one. The impact sends your car spinning off the icy roads and straight into a mound of snow with a mighty &quot;VOOMPF!&quot;\n\nLuckily, your head safely hits the quickly inflated airbag and no part of you seems to be seriously injured. Except for maybe your pride.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Inside car"]()
        return

    def tiddler167(self):
        self.text += """The restaurant is a Deady's, a fast food chain that quickly cropped up across the world after the Machine became an international pop sensation.\n\nTheir slogan is “You Only Live Once!” which, when translated from marketing speak and into English, basically means “You know how you’re going to die, so until then you may as well enjoy yourself by clogging your arteries with as much of our disgustingly/deliciously unhealthy food as possible.”\n\nPeople who pulled FOOD PIOSONING from the Machine receive a card that gives them a permanent 5% discount. Well, after they sign a waiver, that is.\n\nYou take a look at some of the menu “highlights.”\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Menu"]()
        return

    def tiddler168(self):
        self.text += """You grab Jovi and hold him out in front of you at arm’s length. The man stares at it with menace in his eyes, snarling &quot;You.&quot; \n\nHe swings at the standee, knocking the head clean off Jon Bon Jovi's shoulders, moments before a group of patrons rush to restrain the chair man.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Outta here"]()
        return

    def tiddler169(self):
        self.text += """You examine the framed photographs hanging on the wall.\n\nThe first is of a middle-aged blonde woman, smiling as she rests a hand on the side of a hazel horse.\n\nThe second appears to be a photo of John, albeit when he was a couple decades younger, proudly holding a large fish.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

    def tiddler170(self):
        self.text += """&quot;It means nothing!&quot; David answers, almost bringing the ceiling down due to him neglecting his inside voice. &quot;Do you think I would have become the person I am today if I let my death hold me back? No!&quot; He slams his hand on the table to prove just how serious he is.\n\n&quot;I ignored it and built this company out of nothing but my blood, sweat, tears, and a large inheritance from my grandparents! You’re card is nothing but a coincidence. You'll have to deal with it.&quot;\n\n\n\n"""
        self.current_links += ['Quit', 'Leave meeting']
        self.actions += ['&quot;No. I quit.&quot;', 'Leave the room and go to your desk.']
        return

    def tiddler171(self): # good ending
        self.text += """You carefully take apart the gun, throw a couple pieces into the ocean, and store the rest about your person to dump elsewhere.\n\nYou hear the scampering of little feet behind you and turn to see Bon Jovi joyously run to the shore, playfully running towards and away from the waves as they move in and out before he comes up to you.\n\n&quot;Hello, Bon Jovi,&quot; you say.\n\n&quot;Wuff!&quot; he responds.\n\nYou crouch down and give him a pat without a second thought. It feels good to be in control of your fear.\n\nAfter all, it's your life. It's now or never. You ain't gonna live forever. You just want to live while you're alive.\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler172(self):
        self.text += """He looks down at the table. &quot;I s'pose I didn't do a great job hiding the stains.&quot; He lifts up the cloth and peeks under it for a moment. &quot;I used to fish a lot. One day I came home and there were too many dishes on the sink, so I just did the filletin' on the table. Turned out it stained more than I thought it would.&quot;\n\n&quot;Sarah really let me have it that night.&quot; A grin cracks across his face.\n\n"""
        self.params['sarah'] = 1
        self.current_links += []
        self.actions += []
        self.methodDict["Time to talk"]()
        return

    def tiddler173(self):
        self.text += """Rachel waves goodbye as you begin the long drive home. After a few minutes, you turn the radio on to break the silence.\n\n&quot;Shot... through the heart... it's all part... of the game that we call love!&quot;\n\n&lt;html&gt;&lt;center&gt;&lt;h1&gt;THE END&lt;/h1&gt;&lt;/html&gt;\n\n\n\n"""
        self.current_links += ['Outside the karaoke bar', 'The beginning']
        self.actions += ['What if you had done things differently?', 'What if you had been bestowed a different fate?']
        return

    def tiddler174(self):
        self.text += """She raises an eyebrow at you. &quot;You know, watching how people react to their tickets and trying to guess their deaths.&quot; She begins to munch on a turkey sandwich. &quot;It's how I kill time on my lunch break.&quot; \n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Another"]()
        return

    def tiddler175(self):
        self.params['oldAge'] = 1
        self.params['oldAgePlayed'] = 1
        self.params['phone'] = 0
        self.params['carWait'] = 0
        self.params['car'] = 0
        self.params['ignition'] = 0
        self.params['wentOut'] = 0
        self.params['lost'] = 0
        self.params['axeAsk'] = 0
        self.params['seePoison'] = 0
        self.params['getPoison'] = 0
        self.params['poisonCount'] = 0
        self.params['poisoned'] = 0
        self.params['inBedroom'] = 0
        self.params['manWait'] = 0
        self.params['lookCloth'] = 0
        self.params['lookedKitchen'] = 0
        self.params['getBullets'] = 0
        self.params['waitingForHelp'] = 0
        self.params['sarah'] = 0
        self.params['askLooking'] = 0
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

    def tiddler176(self):
        self.text += """She shrugs. &quot;It's fun watching how people react. To see what it says about them and the lives they've lived, and the life they'll live from that point. It gets me to look back at my own life, too. To reflect or whatever.&quot; She chews her sandwich some more. """
        if self.params['poop'] == 1:
            self.text += """&quot;Also, sometimes I meet people who think explosive diarroiah can be a cause of death.&quot;\n\n\n"""
        self.current_links += ['Her']
        self.actions += ['&quot;What did your slip say?&quot;']
        return

    def tiddler177(self):
        self.text += """An A.B. A bed of thick fries, with a load of marinated lamb dumped on top, which is then smothered with cheese and chilli sauce.\n"""
        if self.params['coins'] < 5:
            self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;Tragically (or perhaps luckily), you're not carrying enough money to experience this culinary curiosity."""
        if self.params['coins'] >= 5:
            self.current_links += ['Eating an A.B.']
            self.actions += ['Buy one for five dollars.']
        self.current_links += ['Menu']
        self.actions += ['See what else is on offer.']
        return

    def tiddler178(self):
        if self.params['lost'] == 0:
            self.text += """You head into what you believe is the right direction, but really you have no idea of knowing. \n\nIf you were anyone else, you may be a little worried right about now. But not you. You know how you're going to die, and it's not hypothermia. Hell, you could be naked right now and still survive. Maybe... maybe you SHOULD get naked?\n\nNo. No, that is not a good idea.\n"""
            self.current_links += ['Lost', 'Lost', 'Lost', 'Lost']
            self.actions += ['Go east.', 'Go west.', 'Go north.', 'Go south.']
        if self.params['lost'] == 1:
            self.text += """You trudge through the snow some more, likely just getting yourself more lost than before.\n\nYou feel yourself constantly shivering and becoming a little drowsy. \n\nNothing to worry about.\n"""
            self.current_links += ['Lost', 'Lost', 'Lost', 'Lost']
            self.actions += ['Go east.', 'Go west.', 'Go north.', 'Go south.']
        if self.params['lost'] == 2:
            self.text += """You stumble over your next few steps and feel your breathing start to slow. It may be time to admit that you should be worried.\n\nBut The Machine is never wrong! It said old age!\n\n"""
            self.current_links += ['Lost', 'Lost']
            self.actions += ['Stumble this way.', 'Stumble that way.']
        if self.params['lost'] == 3:
            self.text += """As you continue to make your way through the snow, a growing hatred of The Machine powers you on.\n"""
            self.current_links += ['Lost', 'Lost']
            self.actions += ['Stagger this way.', 'Stagger that way.']
        if self.params['lost'] == 4:
            self.text += """You push forward, fighting the cold, your body on the verge of completely shutting down.\n\nThen, in the distance, you see a light.\n\n"""
            self.current_links += ["There's a light"]
            self.actions += ['Go towards the light.']
        self.params['lost'] = self.params['lost'] + 1
        return

    def tiddler179(self):
        self.text += """\n&lt;html&gt;&lt;h1&gt;&lt;center&gt;ONE MONTH LATER&lt;/p&gt;&lt;/h2&gt;&lt;/center&gt;&lt;/html&gt;\n\nYou're startled awake by the sounds of car horns outside. You yawn and reach over to your beside table to check the time"""
        if self.params['win'] == 1:
            self.text += """, accidentally knocking your Wee Rex Adorable Plush to the floor in the process"""
        self.text += """.\n\nCRAAAAAAAAAAAAAAP!\n\nYou overslept again! Really, you should buy an alarm clock that functions correctly, but the pizza stains on this one hold sentimental value. \n\nNow you only have thirty minutes """
        if self.params['fired'] == 0:
            self.text += """to meet the potential new clients you've been sent to woo. If you screw this up, your career at Albatross Airways is out the window like... an albatross flying out a window."""
        if self.params['fired'] == 1:
            self.text += """to get to your job interview and knock the socks off the Ruby Blue Airways head honchos!"""
        self.text += """\n\nTime to get ready in record time, while still being half-presentable!\n"""
        self.params['timePassed'] = 0
        self.params['timeToGo'] = 30
        self.params['reflected'] = 0
        self.current_links += ['So clean', 'Rank']
        self.actions += ['Have a brisk, yet thorough shower. (Seven minutes)', 'Cleanliness is overrated! Settle for a quick rinse. (Four minutes)']
        return

    def tiddler180(self):
        self.text += """No time for such trivial things as bodily functions! You strut into the appointed room.\n"""
        self.params['didPee'] = 0
        self.current_links += []
        self.actions += []
        self.methodDict["Showtime!"]()
        return

    def tiddler181(self):
        self.text += """You search through the drawers. They're mostly empty aside from a few blunt utensils. Pointless discoveries.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

    def tiddler182(self):
        self.text += """You remember the gun hidden in your pants, but it seems it wasn't hidden enough. The crazed man sees it under your shirt and grabs it before you can stop him.\n\nHe waves it wildly in the air! &quot;Turn the music off!&quot; he screams. &quot;I'm not ready yet!&quot;\n\n\n\n\n"""
        self.current_links += ["Did you forget he's not real?", 'Your goose is cooked!', 'Wrestle']
        self.actions += ['Use Bon Jovi as a shield!', 'Duck! DUCK!', 'Try to wrestle the gun back off him!']
        return

    def tiddler183(self):
        self.text += """You approach The Machine, which has the very charming street name of The Machine of Death.\n\nThe device has only been around for a few years, but it's already hard to imagine a world without it, as it completely reshaped it, creating a culture of death. Well, others feel that it created a culture of life, despite it clearly ruining a few people's.\n"""
        if self.params['machine'] == 0:
            self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;Here's how it works: a person inserts a dollar and sticks their finger in the machine, which takes a blood sample. A little card is then spat out, which reveals the persons final fate.\n\nOf course, it's not that simple. The machine is always 100% accurate, but the cards are often obtuse and even misleading, such as the tragic person who received PEANUTS, spent years avoiding the faux nut, only to have a box full of Snoopy comics fall on top of and kill them. \n\nEvents like this have led some to believe that the machine has a sense of humour.&lt;html&gt;&lt;/br&gt;&lt;/html&gt;"""
        self.text += """\nYou never did get yourself tested. """
        if self.params['coins'] == 0:
            self.text += """And it looks like you won't be doing it today, as you're out of change.\n"""
        if self.params['coins'] > 0:
            self.text += """&lt;html&gt;&lt;/br&gt;&lt;/html&gt;Maybe today is the day. \n"""
            self.current_links += ['Death']
            self.actions += ['Insert a coin.']
        self.params['machine'] = 1
        self.current_links += ['Watch', 'A slip of paper', 'Standing in a mall']
        self.actions += ['Stand back and watch people use the Machine.', 'A slip of paper is stuck to the side of the Machine. Examine it.', 'Return your eyes to the mall.']
        return

    def tiddler184(self):
        self.text += """You look at your co-workers. Their wide, emotionless eyes are fixated on David, each of their faces infected with a hideous grin stretching across them.\n\nWill you one day become like them?\n\n"""
        if self.params['meeting'] == 1:
            self.methodDict['Meeting 1']()
        if self.params['meeting'] == 2:
            self.methodDict['Meeting 2']()
        if self.params['meeting'] == 1:
            self.params['meeting'] = 2
        if self.params['meeting'] <= 2:
            self.current_links += ['Logo', 'David']
            self.actions += ['Look at company logo.', 'Look at David.']
        return

    def tiddler185(self):
        self.text += """You look at the company logo hanging on the far wall. It states the company's name, Albatross Airways, in large blue letters. Above it is a picture depicting a giant albatross surfing a plane. Or perhaps it's a regular-sized albatross surfing a tiny plane?\n\n"""
        if self.params['meeting'] == 1:
            self.methodDict['Meeting 1']()
        if self.params['meeting'] == 2:
            self.methodDict['Meeting 2']()
        if self.params['meeting'] == 1:
            self.params['meeting'] = 2
        if self.params['meeting'] <= 2:
            self.current_links += ['Logo', 'David']
            self.actions += ['Look at company logo.', 'Look at David.']
        return

    def tiddler186(self):
        self.text += """You sip some of the hot tea.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Returns"]()
        return

    def tiddler187(self):
        self.text += """&quot;It makes me feel normal,&quot; she admits. &quot;Not that I'm as weird as everyone says. But people treat me differently because I have lots of money.&quot; She stares at the ground.\n\n&quot;I don't mean to 'slum it,' and I know how damn lucky I am; that's why I try to volunteer a lot. But sometimes I just want to forget about it all and let go.&quot;\n\n&quot;Besides, I love to sing even if not everyone loves hearing me,&quot; she says with a laugh. &quot;I'm going to go let Bonny have a run. """
        if self.params['toldRachel'] == 1:
            self.text += """You better be careful around him,&quot; she adds with a mischievous grin. """
        self.text += """&quot;We'll be right back.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["The choice"]()
        return

    def tiddler188(self):
        self.text += """The colour of this wig is that of a dark brunette, and is rough to touch. The hair is fairly short. Underneath the wig stand is a label that reads &quot;Henry.&quot;\n\n\n\n"""
        self.current_links += ['Blonde', 'Bedroom']
        self.actions += ['Examine the blonde wig.', 'Examine the rest of the bedroom.']
        return

    def tiddler189(self):
        self.text += """&quot;Poisoning, just like that damn Machine said. Accidental. I’m only consoled knowing it was painless and that she still ‘ad a long life.&quot;\n\nHe pauses. &quot;I ‘aven’t been out much since then. Been nice to talk to someone again. Maybe you're a sign from Sarah that I need to keep on livin' while I'm here.&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Time to talk"]()
        return

    def tiddler190(self):
        self.text += """&quot;Go fuck yourself,&quot; you mumble under the breath. &quot;Hahaha! I would if I could!&quot; replies David. &quot;Also, you're fired. Don't let the door hit you on the way out, because I don't want ass prints on my door.&quot;\n\n"""
        self.params['fired'] = 1
        self.current_links += []
        self.actions += []
        self.methodDict["Later"]()
        return

    def tiddler191(self):
        self.text += """You open the pantry door, switch on the light, and gaze at the contents within.\n\nIt's quite bare. Tubs of flour and sugar, a few boxed and canned goods, and sacks of vegetables on the floor.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

    def tiddler192(self):
        self.text += """&quot;Take that last guy. He seemed pretty relieved when he looked at his ticket. I'm going to guess that he's been feeling a burning sensation when peeing lately.&quot; She giggles gleefully to herself.\n\nThe machine is often used as a self-diagnosing tool. Instead of going to a doctor, they would just get a jabbed to see if they were suffering from anything serious. This practice was naturally met with much disapproval from medical professionals.\n\n&quot;Check it out, here comes some more,&quot; she says as she chews on her sandwich.\n\nA group of teenagers approach the machine with jovial spirits, egging one of their friends on to get jabbed, then cheer deafeningly as he does so. He pulls out a slip and they all begin to laugh, the jabbed laughing as he seemingly mimes his own head exploding.\n\n&quot;So,&quot; the deathspotter asks before taking another bite of her sandwich, &quot;What do you think he got?&quot;\n\n\n\n\n\n\n\n"""
        self.current_links += ['Suicide', 'Diarroiah', 'Uninterested']
        self.actions += ['&quot;Suicide.&quot;', '&quot;Explosive diarroiah.&quot;', "&quot;I'm not interested.&quot;"]
        return

    def tiddler193(self):
        self.text += """She smiles, though a quizzical expression remains on her face.\n\n&quot;Well, try to relax and enjoy yourself. I'm supposed to be the crazy one, remember?&quot;\n\nAs you walk by the standee towards a table, you stop in your tracks as a familiar melody flows from the speakers. You turn to the stage to see a middle-aged businessman begin to belt out the most terrifying words you could ever here.\n\n&quot;Shot... through the heart... it's all part... of the game that we call love!&quot;\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Not over until the chiselled rocker sings"]()
        return

    def tiddler194(self):
        self.text += """A middle-aged woman approaches the machine and gets her finger jabbed. She hesitates before reading her slip, finally relenting and peering at the uppercase letters that will set her fate in stone. She begins to cry.\n\nAfter a brief moment of silence, the nameless deathspotter speaks. &quot;Let's not guess that one. This can be a depressing hobby sometimes.&quot; She nibbles her turkey sandwich a little more and turns to you. &quot;So, have you been jabbed?&quot;\n\n\n\n"""
        self.current_links += ['Uninterested', 'Unjabbed', 'You first']
        self.actions += ['&quot;None of your business.&quot;', '&quot;No.&quot;', '&quot;Have you?&quot;']
        return

    def tiddler195(self):
        self.text += """&quot;Well, careful if you do it. It can change the way you live life. And usually not in a good way.&quot;\n\n\n\n"""
        self.current_links += ['Why', 'Her']
        self.actions += ['&quot;Why do you deathspot?&quot;', '&quot;What did your slip say?&quot;']
        return

    def tiddler196(self):
        self.text += """No time to lose! You cram the tofu dog in your mouth as you dash down the street, drops of mango chutney dripping over you. Goodness, you can't take yourself anywhere!\n\n"""
        self.params['timePassed'] = self.params['timePassed'] + 2
        self.params['cleanEat'] = 0
        self.current_links += []
        self.actions += []
        self.methodDict["Busted"]()
        return

    def tiddler197(self):
        self.text += """As you go for the door, you hear David calling your name. \n\n&quot;Just one thing before you go,&quot; he begins. &quot;If you're ever late again, I'll kick your ass so hard that you'll be able to build a pool in the footprint.&quot;\n\nIt's hard to tell if he's trying to be humourous or not.\n\n\n\n\n"""
        self.current_links += ['Sir', 'Fuck', 'Butt']
        self.actions += ['&quot;Yes, Sir.&quot;', '&quot;Go fuck yourself.&quot;', '&quot;Are you saying I have a big butt?&quot;']
        return

    def tiddler198(self):
        self.text += """You find the least stain covered outfit among your floordrobe and slip it on. You have a quick whiff and decide it would be best to drown the garment in deodorant.\n\n"""
        self.params['timePassed'] = self.params['timePassed'] + 3
        self.params['dressedWell'] = 0
        self.current_links += []
        self.actions += []
        self.methodDict["Rumbly tummy"]()
        return

    def tiddler199(self):
        self.text += """You consider going outside and risking the cold weather again despite your current state, but though The Machine has never been wrong before, you certainly don't want to be the first person to prove that it's not infallible.\n\n"""
        self.current_links += []
        self.actions += []
        self.methodDict["Kitchen"]()
        return

def GetSimulator(storyName, doShuffle):
    # this method returns simulator, state/action vocabularies, and the maximum number of actions
    if storyName.lower() == "fantasyworld":
        with open(os.path.join(curDirectory, "fantasyworld_wordId.pickle"), "r") as infile:
            dict_wordId = pickle.load(infile)
        with open(os.path.join(curDirectory, "fantasyworld_actionId.pickle"), "r") as infile:
            dict_actionId = pickle.load(infile)
        return FantasyWorldSimulator(os.path.join(curDirectory, "fantasyworld_actionId.pickle")), dict_wordId, dict_actionId, 222 # 35
    if storyName.lower() == "savingjohn":
        with open(os.path.join(curDirectory, "savingjohn_wordId.pickle"), "r") as infile:
            dict_wordId = pickle.load(infile)
        with open(os.path.join(curDirectory, "savingjohn_actionId.pickle"), "r") as infile:
            dict_actionId = pickle.load(infile)
        return SavingJohnSimulator(doShuffle, os.path.join(curDirectory, "savingjohn.pickle")), dict_wordId, dict_actionId, 4
    if storyName.lower() == "machineofdeath":
        with open(os.path.join(curDirectory, "machineofdeath_wordId.pickle"), "r") as infile:
            dict_wordId = pickle.load(infile)
        with open(os.path.join(curDirectory, "machineofdeath_actionId.pickle"), "r") as infile:
            dict_actionId = pickle.load(infile)
        return MachineOfDeathSimulator(doShuffle), dict_wordId, dict_actionId, 9

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description = "Text game simulators.")
    parser.add_argument("--name", type = str, help = "name of the text game, e.g. savingjohn, machineofdeath, fantasyworld", required = True)
    parser.add_argument("--doShuffle", type = str, help = "whether to shuffle presented actions", required = True)
    args = parser.parse_args()

    startTime = time.time()
    mySimulator, dict_wordId, dict_actionId, maxNumActions = GetSimulator(args.name, args.doShuffle == "True")
    numEpisode = 0
    numStep = 0
    while numEpisode < 10:
        (text, actions, reward) = mySimulator.Read()
        print(text, actions, reward)
        if len(actions) == 0 or numStep > 250:
            terminal = True
            mySimulator.Restart()
            numEpisode += 1
            numStep = 0
        else:
            terminal = False
            playerInput = input()
            # playerInput = random.randint(0, len(actions) - 1)
            print(actions[playerInput])
            if mySimulator.title == "FantasyWorld":
                mySimulator.Act(actions[playerInput]) # for FantasyWorld, Act() takes a string as input
            else:
                mySimulator.Act(playerInput) # playerInput is index of selected actions
            numStep += 1
    endTime = time.time()
    print("Duration: " + str(endTime - startTime))
