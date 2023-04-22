🎶 *It's not a game; I'm not a robot AI challenging you...* 🎶

Except this is a game; the name of the game is Cluedo, and you are indeed being challenged by a robot AI.

# This is `python-cluedo` 🕵️

The `python-cluedo` suite is software for the 70-year-old board game Cluedo (Clue in North America). It is written in Python (because why the heck else would its name start with "Py") and it includes the following components:

1. The powerful Cluedo bot.
2. The Cluedo game simulator.
3. The Cluedo game assistant.
4. Artifacting and dashboard tools.

Each of these components are described in the following subsections. Warning: The following prose is increasingly snarky.

## 1. The powerful Cluedo bot

> *A software implementation of Cluedo would be nothing without an unbeatable bot.*

The bot (or AI, if you *must* call it that) is guaranteed to isolate the correct crime. The bot will win by doing so faster than an expert human player (unless that human is running the bot on their computer!).

The bot will solve the crime correctly even if the bot is acting as a bystander to the game and *never sees any cards that aren't mandatory to see*. That is, the bot can be used as a game observer who does not affect the gameplay (except perhaps by making the players nervous), or the bot can be used as a player who makes decisions which affect gameplay.

**The bot as an observer:** When the bot is used as an observer to a game, it regularly collects information of the gameplay and tries to isolate a solution to the crime. If not shown any of the extra "rumor" cards at the beginning of the game, it identifies when knowing those extra cards are all that stands between it and the solution. Subsequently looking at those cards is the only time when any cards are revealed to the bot, after which the bot solves the crime.

**The bot as a player:** When the bot is used as a player of the game, it does everything that it does as an observer to the game, but it also interacts with the other players. The bot will solve the crime faster because it can *start rumors* to *see rumor cards* that other players possess, thus more directly ruling out the possibilities of the crime. The bot also chooses what cards to show other players in answer to their rumors, thus affecting their deduction.

## 2. The Cluedo game simulator

> *How do you test the bot? How do you benchmark it against other bots or players under controlled, reproducible conditions? You use the Cluedo game simulator.*

The Cluedo game simulator sets up and runs virtual games of Cluedo on the computer between an arbitrary number of players. The players can be bots (with different strategies), humans (with worse strategies), or a mix of both.

Humans playing the computer game receive gameplay information from the simulation and enter their decisions in real-time.

Like human players, bot players must answer others' rumors, start their own rumors, and attempt to solve the crime. However, because each bot is so clever and the underlying software is written so efficiently, one simulated game takes only seconds and some twenty turns before *every* bot has solved the crime. And because each game setup and gameplay has (pseudo) random elements, multiple simulator runs are readily used to compare bots and rule out the luck-of-the-draw.

## 3. The Cluedo game assistant

> *Don't know what strategy to use? Running out of space on your notepad? Questioning your prospects as a detective? Is this somehow the first time you and the fam are playing this timeless classic? Worry not! With the Cluedo game assistant, you'll take all the fun out of the game for everyone and you'll never have to play again!*

Not unlike the Cluedo game simulator, the Cluedo game assistant allows bot and human interaction. However, the bot and the squishy jelly organism (you) are on the same side and both of you, together in symbiosis, are against the other players. The mission: Win family game night and put a stop to its shenanigans as quickly as possible.

With you as its eyes, ears, and hands, the Cluedo game assistant is your brain. You heard that right – having a brain is not a prerequisite for using the assistant. Where it is your responsibility to sneakily type in the rumors that players are starting and answering, and to enact decisions on behalf of the assistant, it is the assistant's role to take the guesswork (and fun) out of the game by solving the crime for you as quickly as possible.

## 4. Artifacting and dashboard tools

...

# TODOs

- game board

# Installation

...

# Getting started

...

# References

...
