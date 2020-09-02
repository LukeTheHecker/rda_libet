import numpy as np
import time
def insert(arr, piece):
    ''' Takes an array of values and a smaller array of values and 
    inserts the smaller array at the back without changing the 
    larger arrays size.
    Parameters:
    -----------
    arr : list/numpy.ndarray, an array of values
    piece : int/float/list/numpy.ndarray, a single value or array of values to insert at the end.
    '''
    assert type(arr) == list or type(arr) == np.ndarray, "arr must be of type list or numpy.ndarray but is of type {}".format(type(arr))
    # in case of piece being a single value: put in list
    if type(piece) == int or type(piece) == float:
        piece = [piece]

    piecelen = len(piece)
    new_arr = np.zeros((len(arr)))
    new_arr[0:-piecelen] = arr[piecelen:]
    new_arr[-piecelen:] = piece

    return new_arr

class Scheduler:
    def __init__(self, list_of_functions, start, interval):
        self.list_of_functions = list_of_functions
        self.start = start
        self.interval = interval
        self.cnt = 1
        self.run_hist_intervals = []
        print("Initialized Scheduler")

    def run(self):
        end = time.time()
        current_time = round(end-self.start, 1)

        # Check if we maybe missed a round:
        target_time = round(self.interval * self.cnt, 1)
        # If difference between current time and the time when we want to start an interview is 
        # larger than two intervals we must have skipped something (because of timing issues).
        if current_time != 0 and (current_time - target_time) >= self.interval*2:
            self.cnt = int(round(current_time / self.interval))
            # print(f"missed at least a round, adjusting self.cnt to {self.cnt:.0f}!")

        # Execute all functions if interval is given
        if current_time  != 0 and current_time % target_time == 0:
            # print(f"Run functions {[t.__name__ for t in self.list_of_functions]} at {current_time}")
            self.run_hist_intervals.append(current_time)
            self.cnt += 1
            [fun() for fun in self.list_of_functions]
