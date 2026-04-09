# Cluedo SAT Problem

What does Cluedo have to do with digital circuit design? Boolean logic.

Cluedo can be solved as a [boolean satisfiability (SAT) problem](https://en.wikipedia.org/wiki/Boolean_satisfiability_problem). A SAT problem is a special case of constraint problem, consisting of boolean variables rather than integer or real variables. A SAT problem consists of a collection of boolean equations in terms of a collection of boolean variables to solve for. Much like a system of linear equations, there can be zero, one, or multiple solutions depending on the number of variables and equations and how independent they are.

Here we formulate the SAT problem for Cluedo. `python-cluedo` uses the [PySAT](https://pysathq.github.io/) solver to find one or more solutions to the SAT problem. [Python EDA](https://pyeda.readthedocs.io/en/latest/index.html), a library for electronic design automation, offers similar functionality.

First, the SAT problem is defined in terms of variables specifying the location where each rumor card exists &ndash; in a player's hand, in the "case file", or among the extra cards. The following notation is used:

- ${X\,}_\text{rumor card}^\text{location}$ is a boolean variable (also known as a _literal_ in the SAT context) indicating whether a given rumor card is in a given location (a player's hand, or the case file, or the extra cards). In the code, this is represented by `CardIsInLocation`. In a non-boolean version of the problem, ${X\,}_\text{rumor card}^\text{location}$ could be replaced by probability $P(\text{rumor card is in location})$, which converges to 0 or 1.

- $\neg$ is the [NOT operator](https://en.wikipedia.org/wiki/Negation). In the code, this is represented by `Not`.

- $\lor$ is the [OR operator](https://en.wikipedia.org/wiki/Logical_disjunction), whose output is truthy if any of its inputs are truthy. In the code, this is represented by `Or`.

- $\oplus$ is the [XOR operator](https://en.wikipedia.org/wiki/Exclusive_or), whose output is truthy if and only if exactly one of its inputs are truthy (they are mutually exclusive). In the code, this is represented by `Xor`.

## Conjunctive Normal Form

[Conjunctive Normal Form (CNF)](https://en.wikipedia.org/wiki/Conjunctive_normal_form) is a standard way of expressing one or more boolean statements. By expressing a SAT problem in CNF, it can be solved by many SAT solvers which accept problems formulated in CNF.

A boolean statement is in CNF if it consists of an $n$-ary [AND operation ($\wedge$)](https://en.wikipedia.org/wiki/Logical_conjunction) of clauses. Each clause consists of an $n$-ary OR operation ($\vee$) of boolean variables or NOT operations ($\neg$) thereon. This is analogous to a product of sums. CNF is easier to understand by seeing examples of valid CNF statements:

- $(A \vee \neg B) \wedge (C \vee \neg D \vee E) \wedge \neg F$
- $A \vee \neg B$ (valid even with no outer $\wedge$s)
- $A \wedge C \wedge \neg F$ (valid even with no inner $\vee$s)

The same variable can be repeated multiple times within a given CNF statement.

Statements such as $A \wedge \neg A$ (which is logically impossible/untrue) or $A \vee \neg A$ (which is always true, regardless of the value of $A$) are still valid CNF.

A collection of boolean statements in CNF can be combined into one boolean statement using the AND operator ($\wedge$), because all of the statements must be true. The result is also valid CNF:

$$
\left\{
\begin{array}{l}
A \vee \neg B \\
A \wedge C \wedge \neg F
\end{array}
\right\}
\quad \Longleftrightarrow \quad
\underbrace{(A \vee \neg B)}_\text{1st statement} \wedge \underbrace{A \wedge C \wedge \neg F}_\text{2nd statement}
$$

When formulating the Cluedo SAT problem, we use the XOR operator ($\oplus$). In the two-operand case, an XOR statement can be converted to CNF as follows:

$$
A \oplus B = (A \vee B) \wedge (\neg A \vee \neg B)
$$

This generalizes to the $n$-ary case:

$$
\bigoplus_i^n A_i \quad = \quad \bigvee_{i \, = \, 1}^n A_i \quad \wedge \quad \!\!\!\!\!    \bigwedge_{\scriptsize \begin{array}{c} i, j \in \\ \text{2-combos} \\ \text{of} \ 1 \dots n \end{array}} \!\!\!\!\! ( \neg A_i \vee \neg A_j )
$$

## General Knowledge of the Game

This section lists the SAT statements based on the fundamental setup of Cluedo rather than any specific game of Cluedo.

Firstly, the case file contains exactly one character, weapon, and room:

> $$\begin{aligned} & {\bigoplus\,}_{\text{character} \ \in \ \text{characters}} \, {X\,}_\text{character}^\text{case file} \\ & {\bigoplus\,}_{\text{weapon} \ \in \ \text{weapons}} \, {X\,}_\text{weapon}^\text{case file} \\ & {\bigoplus\,}_{\text{room} \ \in \ \text{rooms}} \, {X\,}_\text{room}^\text{case file} \end{aligned}$$
>
> ```py
> for rumor_cards in (CHARACTERS, WEAPONS, ROOMS):
>     statements.append(
>         Xor(
>             [
>                 CardIsInLocation(rumor_card, CASE_FILE)
>                 for rumor_card in rumor_cards
>             ]
>         )
>     )
> ```

Secondly, each rumor card is located in only one place &ndash; in one player's hand, in the case file, or among the extra cards:

> For each rumor card:
>
> $$\left( {\bigoplus\,}_{\text{player} \ \in \ \text{players}} \, {X\,}_\text{rumor card}^\text{player} \right) \oplus {X\,}_\text{rumor card}^\text{rumor card} \oplus {X\,}_\text{rumor card}^\text{extra cards}$$
>
> ```py
> statements.append(
>     Xor(
>         [
>             CardIsInLocation(rumor_card, loc)
>             for loc in [*player_indices, CASE_FILE, EXTRA_CARDS]
>         ],
>     )
> )
> ```

Thirdly, each player has exactly the $k$ cards assigned to their hand at the beginning of the game, out of $n = 24$ total rumor cards:

> For each player:
>
> $$\text{$k$ of ${x\,}_i^\text{player}$ must be true, the remaining $n - k$ must be false}$$
>
> In SAT problems, this is known as a _cardinality constraint_. In particular, among the possible cardinality constraints, the above is an _equality constraint_ because it states that exactly $k$ must be true, rather than $\leq k$ or $\geq k$. Consider the simplified case of $k = 2$ out of $n = 3$ total cards, as an example. This would be represented by the statement, "the player has only cards 1 and 2, or the player has only cards 1 and 3, or the player has only cards 2 and 3". This is represented by the following SAT statement:
>
> $$\begin{aligned} & ({x\,}_1^\text{player} \wedge {x\,}_2^\text{player} \wedge \neg \, {x\,}_3^\text{player}) \, \vee \\ & ({x\,}_1^\text{player} \wedge \neg \, {x\,}_2^\text{player} \wedge {x\,}_3^\text{player}) \, \vee \\ & (\neg \, {x\,}_1^\text{player} \wedge {x\,}_2^\text{player} \wedge {x\,}_3^\text{player}) \end{aligned}$$
>
> Note that this is in sum-of-products form, also known as [disjunctive normal form (DNF)](https://en.wikipedia.org/wiki/Disjunctive_normal_form). The outer sum consists of [$n \ \text{choose} \ k$](https://en.wikipedia.org/wiki/Binomial_coefficient) products, in $k$ variables. In a real Cluedo game, the highest possible value of $n \ \text{choose} \ k$ is $24 \ \text{choose} \ 10 = 1,\!961,\!256$, which would occur in a two-player game in which each player receives $k = \mathrm{floor}((24 - 3) / 2) = 10$ cards.
>
> In order to use a SAT solver, the SAT statement must be converted from DNF to CNF, or generated in CNF to begin with. [DNF can be converted to CNF](https://en.wikipedia.org/wiki/Conjunctive_normal_form#Basic_algorithm) using boolean algebra or via brute force using a truth table of $2^n = 16,\!777,\!216$ rows. In particular, the DNF statement above converts to a CNF statement with $2^n - (n \ \text{choose} \ k)$ clauses. To avoid the number of clauses increasing exponentially with $n$, [more efficient approaches](https://en.wikipedia.org/wiki/Conjunctive_normal_form#Other_approaches) such as the [Tseitin encoding AKA Tseitin transformation](https://en.wikipedia.org/wiki/Tseytin_transformation) were developed. They introduce a linear rather than exponential number of additional clauses, but also add a linear number of auxiliary variables.
>
> PySAT's cardinality encoding, `CardEnc`, uses these more efficient approaches to represent cardinality constraints in CNF without such large numbers of clauses. In particular, we use `CardEnc.equals` to encode our equality constraint. [Thanks to Axel Kemper for this tip.](https://stackoverflow.com/a/75812441/18303704)

## Player-Specific Knowledge

This section lists the SAT equations specific to a given player, whether based on how the game was set up or &ndash; most importantly &ndash; based on observations during gameplay.

### Player-Specific Knowledge Based on Game Setup

You have your own rumor cards and only those rumor cards:

> For each rumor card:
>
> > If you have the rumor card:
> >
> > $${X\,}_\text{rumor card}^\text{player}$$
> >
> > ```py
> > statements.append(
> >     CardIsInLocation(rumor_card, player.agent_index)
> > )
> > ```
> >
> > Otherwise:
> >
> > $$\neg {X\,}_\text{rumor card}^\text{player}$$
> >
> > ```py
> > statements.append(
> >     Not(CardIsInLocation(rumor_card, player.agent_index))
> > )
> > ```

### Player-Specific Knowledge Based on Gameplay

In each gameplay turn $i$, a player makes a guess &ndash; a (character, weapon, room) triplet &ndash; about what the crime is. Up to two other players reveal one rumor card each from their hand if matching one of the cards in the guess. This always gives you at least some information, regardless of whether any cards are revealed or you are the player to whom they are revealed:

> For each turn $i$:
>
> > For each other player who reveals a rumor card in turn $i$'s guess:
> >
> > > If you are the player making the guess, i.e., the rumor card was revealed to you, then you know the other player has that card:
> > >
> > > $${X\,}_\text{rumor card}^\text{other player who revealed card}$$
> > >
> > > ```py
> > > statements.append(
> > >     CardIsInLocation(
> > >         card_reveal.rumor_card,
> > >         card_reveal.other_player_index,
> > >     )
> > > )
> > > ```
> > >
> > > Otherwise, you only know that the other player has _one of_ the cards in the guess:
> > >
> > > $$\bigvee_{\text{rumor card} \ \in \ \text{guess}[i]} {X\,}_\text{rumor card}^\text{other player who revealed card}$$
> > >
> > > ```py
> > > statements.append(
> > >     EventsUnion(
> > >         [
> > >             CardIsInLocation(
> > >                 rumor_card, card_reveal.other_player_index,
> > >             )
> > >             for rumor_card in game_log_entry.guess
> > >         ]
> > >     )
> > > )
> > > ```
> >
> > For each opportunity in which a rumor card could have been revealed by a player but was not, you know that other player does not have any of the cards in the guess:
> >
> > > For rumor card in guess $i$:
> > >
> > > $$\neg {X\,}_\text{rumor card}^\text{player who did not reveal card}$$
> > >
> > > ```py
> > > statements.append(
> > >     Not(
> > >         CardIsInLocation(
> > >             rumor_card, card_reveal.other_player_index,
> > >         )
> > >     )
> > > )
> > > ```

## PySAT

For input to PySAT, CNF statements such as $(A_1 \lor \neg A_2) \wedge (\neg A_1 \lor A_3)$ are written as:

```py
[[1, -2], [-1, 3]]
```
