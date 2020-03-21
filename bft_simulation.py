import random
import collections
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

substation_list = []

class Substation :
	'''
	Substation class defines the Electrical systems network zone. It controls all the PMUs and local PDCs.
	It maintains a list of PMUs and PDCs under its control. It provides the interface to add PMUs and PDCs
	In reality, there would be multiple instances of Substations in a WAMS ,but for this project for the sake of simplicity 
	we have assumed only one substation and all PMUs and PDCs under it. With a little bit of effort, the simulation can be 
	done across multiple substations.
	
	'''
	pmu_list = [] #List of PMUs 
	pdc_list = [] #List of PDCs
	
	output_signal = [] #Consensus signal after BFT algorithm is run
	
	def __init__(self,subid):
		self.subid = subid
		
	def add_pmu(self,signal_func,faulty=0): # adds a new PMU to its network
	
		if (faulty == 0): #If not faulty, fault parameter =0 by default meaning it is not faulty
			pmu = PMU(self.subid,len(self.pmu_list),signal_func)
		else: #Else, add fault parameter = 1 to PMU to indicate it is faulty
			pmu = PMU(self.subid,len(self.pmu_list),signal_func,1)
		self.pmu_list.append(pmu) #Add to list of PMUs
		return pmu
			
	def add_pdc(self,faulty=0): # adds a new PDC to its network
		if (faulty==0): #If not faulty, fault parameter =0 by default meaning it is not faulty
			pdc = PDC(self.subid,len(self.pdc_list))
		else: #Else, add fault parameter = 1 to PDC to indicate it is faulty
			pdc = PDC(self.subid,len(self.pdc_list),1)
		self.pdc_list.append(pdc) #Add to list of PDCs
		return pdc
		
	def get_pdcs(self): # returns a list of all PDCs  
		return self.pdc_list
		
	def get_pmus(self): # returns a list of all PMUs  
		return self.pmu_list
		
	def build_consensus(self,pmuid=None): # initiates BFT consensus building algorithm periodically
		count = 0
		quorum = [] #list of devices that ultimately reports the value of the signal for transmission to a remote PDC
		output_signal = [None for v in self.pmu_list] #initializes output signal as None for every PMU, in case we cannot reach a consensus
		for pmu in self.pmu_list:
			for pdc in self.pdc_list:
				consensus_val = pdc.get_consensus(pmu.pmuid) #for every PMU and PDC get concensus
				if (consensus_val != None): #if there is a concensus value, append it to the quorum
					quorum.append(consensus_val)
			maxval = most_frequent(quorum) #Every PDC can report a different value, so take the most frequent value and see if the count is 2/3rds, to reach a quorum
			count = quorum.count(maxval)			
			if (count>= (2*len(self.pdc_list)/3)): # Byzantine Fault Tolerance checks for 2/3rd majority 
				output_signal[pmu.pmuid] = maxval #if 2/3rds majority, add it to output signal
		if (pmuid != None): #for this version, we are using this function to report one PMU at a time, not the whole system
			return output_signal[pmuid]
		else:
			return None # not implemented at this time. When implemented it will return output signals for all the PMUs in the WAN

class PMU:

	'''
	PMU class generates the signal. In our case, we generate a waveform indicative of any real life parameter like voltage, 
	power,or phase angle. A PMU, when not faulty, generates and transmits a single value to all the local 
	PDCs. In case they are faulty or compromised, they behave erratically, transmitting random values to the 
	local PDCs. PMU class has an interface by which when called PMU starts transmitting signals for a certain duration 
	determined by the API function.
	'''
	
	def __init__(self,subid,pmuid,sig,faulty=0): # PMU is initialized with a signal function which generates square wave
		self.subid = subid
		self.pmuid = pmuid
		
		if (faulty == 0):
			self.faulty = False
			self.signal = sig
		else:
			self.faulty = True
			self.signal = sig
			
	def start_transmit(self, subst, duration): # PMU starts transmiting signal for specified duration under a particular substation
		
		#plotting coordinates
		x = []
		y = []
		
		pdclist = subst.get_pdcs() #list of PDCs
		initialize_pdcs(pdclist) #initialize PDCs
		
		pdc_signal_per_pdc = [[] for pdc in pdclist] #2D Matrix of PDCs sending signals to other PDCs in the prepare phase of BFT
		
		
		for i in range(duration):
			s = self.signal()
			for pdc in pdclist: #For every PDC send PMU signal it received to other PDCs
				l = pdc_signal_per_pdc[pdc.pdcid]
				if (self.faulty): #If PDC is faulty, ignore PMU signal and send a random signal to other PDCs
					s = self.signal()
				l.append(s)
				pdc.transmit(self.pmuid,s,i) # signal transmitted to the target PDC
				
			
			out = subst.build_consensus(self.pmuid) # at the end of a cycle , substation initiates concensus building 
			
			#assign coordinates for plotting
			x.append(i) 
			y.append(out)
			
		# plots all signals and signal vectors for all PMUs and PDCs for the duration of transmission
		# plots the output 
		# color convention 
		# blue = non- faulty device
		# red  = faulty device
		# green = out put for Remote PDC
		plot_backend = matplotlib.get_backend()
		
		fig = plt.figure()
		str1 = str(self.pmuid)
		fig.canvas.manager.set_window_title('BFT Concensus Algorithm for Signal: PMU'+str1)
		fig.canvas.manager.window.wm_geometry("+%d+%d" % (0, 0))
		
		# draw all bad signals propagated to other pdcs
		f_pdc_count = 0
		for pdc in pdclist:
			if (pdc.faulty != 0):
				f_pdc_count = f_pdc_count+1
		
		for pdc in pdclist:
			l = pdc_signal_per_pdc[pdc.pdcid]
			axis = plt.subplot(len(pdclist)+2,f_pdc_count+1,(f_pdc_count+1)*pdc.pdcid+1)
			
			pmustr = str(self.pmuid)
			if (self.faulty !=0):
				pmustr = pmustr + '(Faulty)'
			if (pdc.faulty == 0):
				axis.set(title='PMU' + pmustr + '=>'+ 'PDC' + str(pdc.pdcid))
				if (self.faulty !=0):
					plt.plot(x,l, marker='|', color='red', drawstyle='steps-pre')
				else:
					plt.plot(x,l, marker='|', color='blue', drawstyle='steps-pre')
			else:
				axis.set(title='PMU' + pmustr + '=>'+ 'PDC' + str(pdc.pdcid) + '(Faulty)')
				plt.plot(x,l, marker='|', color='red', drawstyle='steps-pre')

		ax = plt.subplot(len(pdclist)+2,f_pdc_count+1,(f_pdc_count+1)*len(pdclist)+1)
		ax.set(title= 'BFT CONCENSUS OUTPUT')
		plt.plot(x,y, marker='|', color='green', drawstyle='steps-pre')
		
		column = 0
		for pdc in pdclist:
			if (pdc.faulty != 0):
				column = column + 1

				for p in pdclist:
					axis = plt.subplot(len(pdclist)+2,f_pdc_count+1,(f_pdc_count+1)*p.pdcid+1+column)
					d_array=p.plotting_array[pdc.pdcid]
					axis.set(title='PDC' + str(pdc.pdcid)+ '(Faulty)=>'+ 'PDC' + str(p.pdcid))
					plt.plot(x,d_array, marker='|', color='red', drawstyle='steps-pre')
		
		plt.subplots_adjust(bottom=0.1, right=0.8, top=0.9, hspace=2)
		
		#NOTE: Backend can be different depending on device run
		#I have tried to make it device independent but in case it doesn't run
		#Try it on windows 10 python version 3.7.3 or above
		plot_backend = matplotlib.get_backend()
		mng = plt.get_current_fig_manager()
		if plot_backend == 'TkAgg':
			mng.resize(*mng.window.maxsize())
		elif plot_backend == 'wxAgg':
			mng.frame.Maximize(True)
		elif plot_backend == 'Qt4Agg':
			mng.window.showMaximized()
		
		plt.show()
		
class PDC:

	'''
	PDCs are responsible for interpreting and validating the PMU signals before they are transmitted 
	to non local network. PDCs take the active part in the BFT alogorithm by building signal vectors 
	and taking decisions with simple majority concensus. This is a distributed process and there is no 
	single master node. Every one takes their own descision and notifies its value to build a 
	concensus. Every PDC takes part in consensus building by transmitting correct or faulty signal 
	to the other PDCs. A fauty (Traitor) PDC sends random values whereas a correct PDC retransmits 
	the values it receives from the PMU.
	
	'''
		
	def __init__(self,subid,pdcid,faulty=0):
		self.subid = subid
		self.pdcid = pdcid 
		self.faulty = faulty
		self.signal_matrix = []
		self.plotting_array=[]
		
	def set_faulty(self,faulty): # sets a PDC faulty
		self.faulty = faulty
		
	def init_signal_vectors(self): # refresh the PDC array by intializing them before a new transmission
	
		self.signal_matrix = []
		self.plotting_array=[]
		
		st = substation_list[self.subid] #substation list, only one in our version, but can be more than one, not implemented yet
		no_of_pmus = len(st.get_pmus()) #number of PMUs
		
		for p in range(no_of_pmus):
			self.signal_matrix.append([])
			
		for p in range(no_of_pmus): #Every PDC can handle multiple PMU requests at the same time
			no_of_pdcs = len(st.get_pdcs())
			for n in range(no_of_pdcs):
				row = self.signal_matrix[p]
				row.append(None)
				
		self.init_plotting_array()
				
	def init_plotting_array(self): # helper function for plotting signals
		
		no_of_pdcs = len(st.get_pdcs())
		for n in range(no_of_pdcs):
			self.plotting_array.append([])
			
	def get_consensus(self, pmuid): # gets individual descision for every PDC by looking at signal vector
	
		if (self.faulty>0):
			return signal_generator() 
			
		v = self.signal_matrix[pmuid]
		
		maxval = most_frequent(v) #most frequent value in signal vector
		count = v.count(maxval) #count of most frequent value
		
		# each pdc takes its own descision, should be more than 1/2, simple majority, unlike ultimate BFT consensus which needs 2/3rds majority
		if (count > (len(v)/2)): 
			#print ('PDC consensus:', self.pdcid, 'val=',maxval)
			return maxval
		else:
			#print('no consensus')
			return None
		
		
	def print_signal_vector(self, pmuid): #Utility function for printing signal vector
	
		print('pdc id->', self.pdcid, 'v:', self.signal_matrix[pmuid])
	
	def transmit(self,from_pmu,signal_val,time_stamp_seq): # propagates PMU signal to other PDCs in prepare phase of concensus
		
		v_vector = self.signal_matrix[from_pmu] #signal received for a particular PMU for all PDCS
		v_vector[self.pdcid]=signal_val
			
		subst = substation_list[self.subid] #list of substations, only one for our version, can be more, not implemented yet
		pdcs = subst.get_pdcs() #get list of pDCS for the substation
		
		for pdc in pdcs :
			if (self.pdcid != pdc.pdcid): #No need for PDC to transmit signal to itself
				if (self.faulty ==0): #If not faulty PDC
					pdc.BFT_prepare(from_pmu,self.pdcid,signal_val,time_stamp_seq) #broadcast the correct signal by PMU to all other PDCs
				else: #Else, ignore the PMU signal received and send a incorrect random signal to other PDCs
					s = signal_generator()
					faulty_signal_propagation_to_other_pdc_array = pdc.plotting_array[self.pdcid]
					faulty_signal_propagation_to_other_pdc_array.append(s)
					pdc.BFT_prepare(from_pmu,self.pdcid,s,time_stamp_seq)
			else:
				if (self.faulty> 0): #If faulty, do not plot anything
					faulty_signal_propagation_to_other_pdc_array = pdc.plotting_array[self.pdcid]
					faulty_signal_propagation_to_other_pdc_array.append(None)
		
	def resetPDC(self): #function to reset PDC
		self.signal_matrix = []
		
	def BFT_prepare(self,from_pmu,from_pdc, signal_val, time_stamp_seq): #send signal from one PDC to other PDCs
		
		v_vector = self.signal_matrix[from_pmu]
		v_vector[from_pdc]= signal_val
		
'''
helper functions
'''

def most_frequent(List): # utility function to find simple majority

	if (len(List)<1):
		return None
	counter = 0
	num = List[0] 
      
	for i in List: 
		curr_frequency = List.count(i) 
		if(curr_frequency> counter): 
			counter = curr_frequency 
			num = i 
  
	return num 

			
def signal_generator(): #random signal generator from 0 to 10 amplitude

	return (0.1)*random.randrange(0,100,1)
	
	
def initialize_pdcs(pdclist): # initialize PDCs , flush buffers etc.
	for pdc in pdclist:
		pdc.init_signal_vectors()

'''
main module is responsible for the simulation
shows 5 kinds of scenarios with 2 PMU and 6 PDCs
1. PMU transmitting good signal BFT reaches concensus 
2. Compromised PMU transmitting wrong signal BFT blocks transmission
3. PMU transmitting good signal. PDC No 1 is Faulty/Compromised. BFT reaches consensus 
4. PMU transmitting good signal. PDC No 1 & 3 is Faulty/Compromised. BFT reaches consensus 
5  PMU transmitting good signal. PDC No 1 & 3 & 4 is Faulty/Compromised. BFT blocks signal 
'''

if __name__ == '__main__':


	st = Substation(0)
	substation_list.append(st)
	
	# Creating PMU 1 & 2 
	pmu0 = st.add_pmu(signal_generator,1) #faulty
	pmu1 = st.add_pmu(signal_generator)
	
	# Creating PDC 1 to 6
	#all PDCs are not faulty initially
	pdc0 = st.add_pdc()
	pdc1 = st.add_pdc()
	pdc2 = st.add_pdc()
	pdc3 = st.add_pdc()
	pdc4 = st.add_pdc()
	pdc5 = st.add_pdc()
	
	# Simulation scenario 1
	pmu1.start_transmit(st,10)
	#consensus reached
	
	# Simulation scenario 2
	pmu0.start_transmit(st,10)
	#no consensus reached because PMU itself is faulty
	
	# Simulation scenario 3
	pdc0.set_faulty(1) #set PDC 0 to faulty
	pmu1.start_transmit(st,10)
	#consensus reached from 2/3rds voting
	
	# Simulation scenario 4
	pdc3.set_faulty(1) #set PDC 3 to faulty
	pmu1.start_transmit(st,10)
	#consensus reached from 2/3rds voting
	
	# Simulation scenario 5
	pdc4.set_faulty(1)  #set PDC 4 to faulty
	pmu1.start_transmit(st,10)
	#no consensus reached because 3 PDCs out of 6, which is less than 2/3rds