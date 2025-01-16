class Undo_Redo:
    # this class keeps the logic for und / redo so that it can be used by more than one client without redundant code
    def __init__(self):
        # Undo /Redo control
        #print ("Initializing super")
        self.processid_akt = 0
        self.processid_high = 0
        self.processid_incr = 10
        self.list_processids = []
        self.stack_processids = [] # list
        # Undo /Redo control end
    # Undo /Redo Funktionen

    def reset(self):
        self.processid_akt  = 0
        self.processid_high = 0
        self.list_processids = []
        self.stack_processids = []

    def get_processid_akt(self):
        return self.processid_akt

    def process_undo(self):
        rc = False
        processid_undone = -1
        # if there is a predecessor in list_processids (len > 1):
        #   move processid_akt from list_processids to undo-stack, then apply new act (predecessor) giving the processids from act and undone
        # returns False if nothing can be undone otherwise True
        num_elements = len(self.list_processids)
        if num_elements <= 1:
            rc = False
        else:
            processid_undone = self.list_processids[-1] # last element
            self.stack_processids.append(processid_undone)
            self.list_processids.pop() # removes last element
            self.processid_akt = self.list_processids[-1] # "new" last element
            print (" UNDO List Processids: " + str(self.list_processids) + " REDO Stack Processids: " + str(self.stack_processids) + " apply processid: " + str(self.processid_akt)) if self.debug else True
            rc = True
        return rc, self.processid_akt, processid_undone

    def process_redo(self):
        rc = False
        processid_predecessor = -1
        # if there is an element in stack processids (len > 1):
        #   move last processid from stack processids to list_processids, then apply new act (moved from stack) giving the processids from act and predecessor of list_processids
        # returns False if nothing can be redone otherwise True
        num_elements = len(self.stack_processids)
        if num_elements < 1:
            rc = False
        else:
            processid_predecessor = self.list_processids[-1] # last element
            processid_redone = self.stack_processids[-1] # last element
            self.list_processids.append(processid_redone)
            self.stack_processids.pop() # removes last element
            self.processid_akt = self.list_processids[-1] # "new" last element
            print (" REDO List Processids: " + str(self.list_processids) + " REDO Stack Processids: " + str(self.stack_processids) + " apply processid: " + str(self.processid_akt)) if self.debug else True
            rc = True
        return rc, self.processid_akt, processid_predecessor

    def endis_buttons(self): # disable / enable buttons depending on processids, here the buttons are not accessed, we just return the states
        if len(self.list_processids) > 1:
            rc_undo = 1
        else:
            rc_undo = 0
        if len(self.stack_processids) > 0:
            rc_redo = 1
        else:
            rc_redo = 0
        return rc_undo, rc_redo
        
class Undo_Redo_Diatisch(Undo_Redo):
    def __init__(self, debug):
        super().__init__()
        self.debug = debug
        
    def historize_process(self):
        self.processid_high += self.processid_incr
        self.processid_akt = self.processid_high
        self.list_processids.append(self.processid_akt)
        print (" Historize Diatisch: Processid_akt is now: " + str(self.processid_akt)) if self.debug else True
        
class Undo_Redo_Dateimeister(Undo_Redo):
    def __init__(self, debug):
        super().__init__()
        self.debug = debug
        
    def historize_process(self):
        self.processid_high += self.processid_incr
        self.processid_akt = self.processid_high
        self.list_processids.append(self.processid_akt)
        print (" Historize Dateimeister: Processid_akt is now: " + str(self.processid_akt)) if self.debug else True
    
class Undo_Redo_Camera(Undo_Redo):
    def __init__(self, debug):
        super().__init__()
        self.debug = debug
        
    def historize_process(self):
        self.processid_high += self.processid_incr
        self.processid_akt = self.processid_high
        self.list_processids.append(self.processid_akt)
        print (" Historize Camera: Processid_akt is now: " + str(self.processid_akt)) if self.debug else True




