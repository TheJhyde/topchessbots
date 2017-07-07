#!/usr/bin/env python

import tweepy, time, sys, tracery, chess, subprocess
from random import randint
from tracery.modifiers import base_english

# Two apis, for two different bots
CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_KEY = ''
ACCESS_SECRET = ''

CONSUMER_KEY_TWO = ''
CONSUMER_SECRET_TWO = ''
ACCESS_KEY_TWO = ''
ACCESS_SECRET_TWO = ''

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api_alpha = tweepy.API(auth)

auth_two = tweepy.OAuthHandler(CONSUMER_KEY_TWO, CONSUMER_SECRET_TWO)
auth_two.set_access_token(ACCESS_KEY_TWO, ACCESS_SECRET_TWO)
api_omega = tweepy.API(auth_two)

# The board we'll be storing moves on
board = chess.Board()

# The rules for generating the tweets that tracery will use
rules_alpha = {
	'start': ['', 'I #i_verb# ', "Hello! ", 'You should #should_verb#'],
	'should_verb': ['try', 'use', 'attempt'], 
	'i_verb': ["suggest", "submit", "think you should"],
	'end': ['', '. Thanks!', '. Hooray for chess!', "!!", "!", "!!!"],
	'inner': ['', ' ', ' -> ', ' to ', ' moving to ']
}
rules_omega = {
	'start': ['', 'Please #please_verb# ', 'I #i_verb# ', "Hmmm..... ", "How about "],
	'please_verb': ['try', 'consider', 'attempt'], 
	'i_verb': ["suggest", "submit", "think you should"],
	'end': ['', ', if you don\'t mind', '. Goodnight.', ".", "..."],
	'inner': ['', ' ', ' -> ', ' to ', ' and then... I think... ']
}

grammar_alpha = tracery.Grammar(rules_alpha)
grammar_omega = tracery.Grammar(rules_omega)

grammar_alpha.add_modifiers(base_english)
grammar_omega.add_modifiers(base_english)


def launch():
	print ("I'm starting!")
	minute = 60
	rand = randint(0, 100)
	# I want the bots to submit move for a little less than half of all turns (so they don't dominate)
	# And to occasionally but rarely both submit moves for the same game. I also wanted when they responded
	# to be randomized slightly
	if rand <= 18:
		sleep = randint(5, 55)
		time.sleep(sleep*minute)
		make_tweet(api_alpha, grammar_alpha, 0)
	elif rand <= 36:
		sleep = randint(5, 55)
		time.sleep(sleep*minute)
		make_tweet(api_omega, grammar_omega, 1)
	elif rand <= 41:
		sleep = randint(5, 50)
		time.sleep(sleep*minute)
		make_tweet(api_alpha, grammar_alpha, 0)

		new_sleep = randint(5, 55 - sleep)
		time.sleep(new_sleep*minute)
		make_tweet(api_omega, grammar_omega, 1)
	elif rand <= 46:
		sleep = randint(5, 50)
		time.sleep(sleep*minute)
		make_tweet(api_omega, grammar_omega, 1)
		
		new_sleep = randint(5, 55 - sleep)
		time.sleep(new_sleep*minute)
		make_tweet(api_alpha, grammar_alpha, 0)

# This method actually generates the tweet
def make_tweet(api, grammar, bot):
	most_recent = api.user_timeline('topchessgames', count=1)[0]
	if find_tweet_state(most_recent.text) == 1:
		# Gets the best move for the opening board
		smart_move = best_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 0)
		api.update_status(tweet_text(smart_move))
	elif find_tweet_state(most_recent.text) == 2:
		# Load all the previous moves from this game and generates a FEN from it
		# How many turns there have been in this game
		turns = int(most_recent.text.split(",")[1].replace(' Turn ', ''))
		# Pulls all the tweets from this game
		game_tweets = api.user_timeline('topchessgames', count=turns)
		# Gets the coordinates from those moves and puts them on the python-chess board
		for tweet in game_tweets[::-1]:
			move = convert_tweet(tweet.text)
			translate = chess.Move.from_uci(move)
			board.push(translate)
		fen = board.fen()
		# You could just provide stockfish with the list of moves but that seems to have cause trouble 
		# when you start having a lot of moves. So providing it with a fen seems to be more reliable
		smart_move = best_move(fen, bot)
		api.update_status(tweet_text(smart_move, grammar))

# Takes a tweet and converts it into a format the script can read.
# Removes all the extra text, merges the coordinates into one line
def convert_tweet(tweet):
	return tweet.split(": ")[1][0:8].replace(" to ", "").lower()

# There are three kinds of tweets TCG might make:
# 	0 - Game Ends: "Game {#}, Turn {#}, {move type}: {#} to {#}. {Color} wins! The next game will begin shortly."
# 	1 - Game starts: "Beginning game {#}. Submit moves for white now."
#	2 - Regular turns: "Game {#}, Turn {#}, {move type}: {#} to {#}. You may submit moves for black now."
# This method returns which one, since our response differs depending
def find_tweet_state(text):
	if text.find("Beginning game") != -1:
		return 1
	elif text.find("The next game will begin shortly") != -1:
		return 0
	else:
		return 2

# Uses the tracery grammar to generate a tweet with the move in it.
def tweet_text(move, grammar):
	return grammar.flatten("@topchessgames #start#" + move[0:2] + "#inner#" + move[2:4] + "#end#")

# Launches stockfish and gets the best move for a given board. You can get stockfish at https://stockfishchess.org/
def best_move(fen, bot):
	# Calling 'stockfish' directly worked fine on one of my computers but not on the other, so you may need
	# to replace it with the path to the stockfish utility, i.e. /Users/yourname/topchessbot/stockfish
	stockfish = subprocess.Popen("stockfish", 
		universal_newlines=True, 
		stdin=subprocess.PIPE, 
		stdout=subprocess.PIPE)

	stockfish.stdin.write("uci\n")

	stockfish.stdin.write("setoption name Syzygy50MoveRule value false\n")

	if bot == 0:
		# Bot 0 is reliably pretty good at chess and plays very defensively
		stockfish.stdin.write("setoption name Skill Level value 10\n")
		stockfish.stdin.write("setoption name Contempt value -100\n")
	else:
		# Bot 1 is wildly variable in how good at chess they are and plays very aggresively
		stockfish.stdin.write("setoption name SkillLevel value " + str(randint(0, 20)) + "\n")
		stockfish.stdin.write("setoption name Contempt value 100\n")

	stockfish.stdin.write("ucinewgame\n")
	isready(stockfish)

	stockfish.stdin.write("position fen " + fen + "\n")

	stockfish.stdin.write("go\n")
	stockfish.stdin.flush()

	# It tries 500 times, which should be enough to find the bestmove
	# And if it doesn't, something's terribly wrong and we should just stop instead of continueing to try
	for _ in range(500):
		line = stockfish.stdout.readline()
		if "bestmove" in line:
			return line.split(" ")[1]

# Checks with stockfish to make sure it's ready. I don't know if the program getting ahead of stockfish is 
# Something we need to worry about, but better safe I say.
def isready(stockfish):
	stockfish.stdin.write("isready\n")
	stockfish.stdin.flush()
	while True:
		text = stockfish.stdout.readline().strip();
		if text == "readyok":
			return True;

launch()