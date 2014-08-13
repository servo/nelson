#!/usr/bin/env python

from github import Github
import json
import logging
import logging.handlers
import re
import sys

IGNORED_COMMENTERS = ["bors-servo", "hoppipolla-critic-bot"]

STATE_BAD = -2
STATE_STALE = -1
STATE_DISCUSSING = 0
STATE_UNREVIEWED = 1
STATE_APPROVED = 2
STATE_PENDING = 3
STATE_TESTED = 4
STATE_CLOSED = 5

REVIEWERS = ["metajack", "ms2ger", "larsbergstrom", "jdm", "pcwalton", "simonsapin"]

def state_name(n):
    assert STATE_BAD <= n
    assert n <= STATE_CLOSED
    return [ "BAD",
             "STALE",
             "DISCUSSING",
             "UNREVIEWED",
             "APPROVED",
             "PENDING",
             "TESTED",
             "CLOSED" ][n+2]

class Pull(object):
    def __init__(self, ghpull):
        self.ghpull = ghpull
        self.number = self.ghpull.number

        self.load_head_comments()
        self.load_pull_comments()

        self.state = self.get_current_state()
        if self.ghpull.state == "closed":
            self.state = STATE_CLOSED
        elif self.ghpull.mergeable == False:
            self.state = STATE_STALE
        elif len(self.head_comments) + len(self.pull_comments) > 0:
            self.state = STATE_DISCUSSING
        else:
            self.state = STATE_UNREVIEWED

    def get_current_state(self):
        if self.ghpull.state == "closed":
            return STATE_CLOSED
        elif self.ghpull.mergeable == False:
            return STATE_STALE
        elif len(self.head_comments) + len(self.pull_comments) > 0:
            return STATE_DISCUSSING
        else:
            return STATE_UNREVIEWED


    def load_pull_comments(self):
        self.pull_comments = [
            (c.created_at, c.user.login, c.body) \
            for c in self.ghpull.get_comments()
            if c.user.login not in []
        ]

    def load_head_comments(self):
        comments = self.ghpull.head.repo.get_commit(self.ghpull.head.sha).get_comments()
        self.head_comments = [
            (c.created_at,
             c.user.login,
             c.body)
            for c in comments
            if c.user.login in REVIEWERS and c.created_at == c.updated_at
            and c.user.login not in []
        ]

    def approval_list(self):
        def contains_approval(comment):
            words = comment.split(r"\s+")
            for w in words:
                if w == "r+" or w == "r=me" or re.match(r"^r=(\w+)$", w):
                    return True
            return False

        return [u for (_, u, c) in self.head_comments if contains_approval(c)]

def main():
    fmt = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S %Z")
    rfh = logging.handlers.RotatingFileHandler("nelson.log",
                                               backupCount=10,
                                               maxBytes=1000000)

    # FIXME: add real arg parsing
    if "--quiet" not in sys.argv:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.INFO)
        logging.root.addHandler(sh)

    rfh.setFormatter(fmt)
    rfh.setLevel(logging.INFO)
    logging.root.addHandler(rfh)
    logging.root.setLevel(logging.INFO)

    logging.info("---------- starting run ----------")
    logging.info("loading nelson.cfg")
    cfg = json.load(open("nelson.cfg"))

    logging.info("loading pull requests")
    gh = Github(cfg["gh-user"], cfg["gh-pass"])
    repo = gh.get_user(cfg["owner"]).get_repo(cfg["repo"])



    pulls = [Pull(pull) for pull in repo.get_pulls()]
    for pull in pulls:
        print pull.number
        print state_name(pull.state)
        print pull.pull_comments
        print pull.head_comments
        


if __name__ == "__main__":
    main()

