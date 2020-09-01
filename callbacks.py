import numpy as np


class Callbacks:
    def __init__(self):
        self.allow_presentation = False
        self.permission_statement = ['Allow', 'Forbid']
        self.quit = False
        self.stateChange = 0
    def presentToggle(self, event):
        self.allow_presentation = not self.allow_presentation
        print(f'self.allow_presentation = {self.allow_presentation}')

    def quitexperiment(self, event):
        self.allow_presentation = not self.allow_presentation
        self.quit=True

    def stateforward(self, event):
        self.allow_presentation = not self.allow_presentation
        self.stateChange = 1
    def statebackwards(self, event):
        self.allow_presentation = not self.allow_presentation
        self.stateChange = -1


# Lets design a button