import mwmatching
#import ortools - import the bits we need from it only
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
import exagony
import weightings
import initial_rankings as initial_rankings
from operator import itemgetter


topN_ = ['United States','Canada','England','Australia'] #top N expected teams, for mutual cuts 
top8_ = ['United States', 'Canada', 'England', 'Australia', 'Argentina', 'New Zealand', 'Sweden', 'Finland' ] #top 8 from 2014
 
# edges are (v1,v2,weight)
# vector as input is (e0,e1,e2,...)
# return is (p0,p1,p2,...) where p0 is the vertex id paired with vertex 0, and so on
# mwmatching.maxWeightMatching([(0,1,0),(1,2,100),(2,3,0),(3,0,100)],maxcardinality=True)


#team structure:
#
# id (numeric vertex id) - is just index in list, as we don't sort this list
# name (name of team)
# rating (current rating)
# exagony_vector (geographical grouping) - external to team
# desires_vector (vector of teams and desires to play them)
# eligible_opponents (starts out with all teams, removed by playing them or other cuts)
# weighting_vector (weights the weights between rating, exagony, desires)

teams = [ {'name':i} for i in exagony.teamnames ]
lookup = { teams[i]['name']:i for i in range(len(teams)) }
topN = [ t for t in teams if t['name'] in top8_] #or topN
top8 = [ i for i in range(len(teams)) if teams[i]['name'] in top8_ ]
print topN
#expected topN should never play each other in non-bracket rounds
print top8
for t in teams:
	if t in topN: #or topN
		t['eligible_opponents'] = [ i for i in range(len(teams)) if teams[i] not in topN ]
	else:
		t['eligible_opponents'] = list(range(len(teams)))		
	t['prev_opponents']=[] #no previous opponents
	t['rating'] = initial_rankings.wc2014cats[t['name']] #or we can preweight this
	t['desires_wt'] = 1
	tmp =  weightings.weighting[t['name']] #three weights, should sum to 100? or possibly have pythagorean length 100
	t['weighting_vector'] = tuple([ (i*60)/sum(tmp) for i in tmp]) 
	#and normalise the weighting vector - to total sum of 60 [which has lots of nice prime factors (needs to be integer values)

#amalfi pair weights are symmetric between teams
#this returns a value between 0 and len(teams)-amalfi ... but we want this to be big, not small, so we negate it

#need to ensure this is positive definite now for this implementation - so need "max abs dist" to subtract things from 
#also - move from absolute ranking error relative to amalfi distance to "difference from the difference in rating between the ideal pair"
#which means we are more tolerant of matches to "neighbours" if they're close in expected strength, not just ranking


##############################
#############  Might need to totally rework this completely, based on experience with BC2017 test
def Amalfi_Pair_Weight(team1, team2, amalfi, ordering):
	#ordering[0] is sorted list, ordering[1] is dual of that (the dict mapping team to position)
	#ordering[2] is our offset, the largest possible difference between two rankings (+ve)
	posoffset = ordering[1][team1]+amalfi #ideal positive match
	ideals = [] #list of ideal values to test distance from
	if posoffset < len(ordering[0]): #if this match index is actually in existence:
		ideals.append(teams[team1]['rating'] - teams[ordering[0][posoffset]]['rating'])
	negoffset = ordering[1][team1]-amalfi #ideal negative match
	if negoffset > -1: #this match index actually exists
		ideals.append(teams[team1]['rating'] - teams[ordering[0][negoffset]]['rating'])
	rating_dist = teams[team1]['rating']-teams[team2]['rating'] #actual rating difference
	amal_dist = min([abs(rating_dist-i_dist) for i_dist in ideals]) #distance from closest possible ideal match
	return ordering[2]-amal_dist #is this definitely positive?

#pure rating separation version of the amalfi thing above - more positive values are worse
def Rating_Pair_Weight(team1, team2, amalfi, ordering):
	return 3*abs(teams[team1]['rating']-teams[team2]['rating'])
	#return (teams[team1]['rating']-teams[team2]['rating'])**2


#Exagony is encoded as a geographical vector, from most to least specific
# - code for this is now in exagony.py module

#Exagony Pair Weights are symmetric between teams
#values are 0, 1, 4 (in order of separation) more positive is bad
def Exagony_Pair_Weight(team1, team2):
	return 2*exagony.get_exagony_dist(teams[team1]['name'], teams[team2]['name'])

#not symmetric between teams
#we need to work on how we encode Desires.
#one approach is to have "desire sets" - (top8team), (newteam) etc - and have each team's desires be a list of those sets.
#the weight for each set increases round-on-round if not satisfied, and *all* sets satisfied by a match are removed after that match is made
# more positive is good
def Desire_Weight(team1, team2):
	desires = 0
	if team2 in top8:
		desires = teams[team1]['desires_wt']
	return desires #so, the sum of all desire sets which are satisfied by team 2

def Weight(team1,team2, amalfi, ordering):
	apw = Rating_Pair_Weight(team1, team2, amalfi, ordering)
	epw = Exagony_Pair_Weight(team1, team2)
	dw1 = -6*Desire_Weight(team1, team2)
	dw2 = -6*Desire_Weight(team2, team1)
	#print 'Team {0}v{1}: Rating:{2} Exagony:{3} Desires {4},{5}'.format(team1,team2,apw,epw,dw1,dw2)
	#weight is product_(i=1,2) (ti_aw*apw + ti_ew*epw + ti_dw*dwi)
	w1 = apw*teams[team1]['weighting_vector'][1]+epw*teams[team1]['weighting_vector'][0]+dw1*teams[team1]['weighting_vector'][2]
	w2 = apw*teams[team2]['weighting_vector'][1]+epw*teams[team2]['weighting_vector'][0]+dw2*teams[team2]['weighting_vector'][2]
	return -(w1+w2) #more negative is bad for mwmatching 
	#return value *smaller is better* (more negative is better)

def calc_ordering(teams):
	t = [ (i[0]['rating'],i[1]) for i in zip(teams,range(len(teams)))]
	#larger ratings at *end* (larger index)
	ordered = [ i[1] for i in sorted(t,key=itemgetter(0))] #ordered list of numbers
	ranking = { i[0][1]:i[1] for i in zip(sorted(t, key=itemgetter(0)),range(len(teams)))}
	tmax = max([i['rating'] for i in teams])
	tmin = min([i['rating'] for i in teams])
	offset = tmax - tmin #biggest possible gap
	return (ordered,ranking, offset)

#Produce Pairs for next Round
#Takes: Team State, Amalfi Distance Factor, IF we should use Travelling Salesman (for a complete cycle of teams when combined with previous round's matches)
#Returns: Pair Ids
#Side Effects: Modifies Team State
def pair_round(teams, amalfi, tsp=False, output=True, fullwidth = False):
	ordering = calc_ordering(teams)
	edges = []
	matrix = {}
	for team,i in zip(teams,range(len(teams))):
		for opp in team['eligible_opponents']:
			if opp > i: #we've not done this pairing before
				#generate weightings
				wt = Weight(i,opp,amalfi,ordering)	#amalfi here for "ideal distance" of rating pairing
				#add edge
				edges.append((i,opp,wt))
	#print edges
	#print max(-e[2] for e in edges)
	if (tsp == True):
		#for TSP (for max-weight matching, we just don't add the completed links at all)
		minwt = min(-e[2] for e in edges)
		maxwt = max(-e[2] for e in edges)
		wtrange = maxwt - minwt
		goodwt = minwt - wtrange #very good
		badwt = maxwt + wtrange #very bad
		#print "{0} Good, {1} Bad, {2} min, {3} max, {4} range".format(goodwt,badwt,minwt,maxwt,wtrange)
		#negw = 2 * maxwt #we want the prev opponents, other than the most recent, to be really unpopular
		for team,i in zip(teams,range(len(teams))):
			for opp in team['prev_opponents'][:-1]: #all but last one
				if opp > i:
					wt = -badwt    
					edges.append((i,opp,wt))
			if len(team['prev_opponents']) > 0:
				edges.append((i,team['prev_opponents'][-1],-goodwt)) #the most recent opponent is a *perfect* link, so we always select it (these have twice the weight of anything else)			#for TSP we need a matrix - and we also need the "best" value to be smallest, not largest
		#make matrix of dist
		matrix = {}
		for i in range(len(teams)):
			matrix[i] = {}
			for j in range(i,len(teams)):
				matrix[i][j] = badwt - goodwt
		for e in edges:
			matrix[e[0]][e[1]] = -e[2] - goodwt  #fill in edge weights where they exist
		#print matrix
	#print edges	
	if (tsp == False):
		pair_dests = mwmatching.maxWeightMatching(edges,maxcardinality=True)
	else:
		pair_dests = [None] * len(teams) 
		def Distance(i,j):
			if i < j:
				return matrix[i][j]
			else:
				return matrix[j][i]
		routing = pywrapcp.RoutingModel(len(teams), 1, 0) #create the routing model in Google OR Tools, for 1 route to find, all nodes, start at node 0
		search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()
		
		search_parameters.first_solution_strategy = ( routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC ) 
		#use GUIDED_LOCAL_SEARCH metaheuristic (could also turn on Simulated Annealing, or Tabu Search)
		search_parameters.local_search_metaheuristic = ( routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH )
		search_parameters.time_limit_ms = 60000 #allow 60 seconds of processing to improve the path via above metaheuristic
		routing.SetArcCostEvaluatorOfAllVehicles(Distance)
		assignment = routing.SolveWithParameters(search_parameters)
		if assignment: #we have a solution
			total_weight = assignment.ObjectiveValue()
			index = routing.Start(0) #get first node in route 0 (the only route we look for)
			#we assume that the next value will be the previous pair from the last matching, as that's a zero weight path
			next_idx = assignment.Value(routing.NextVar(index))
			pairs_ = []
			pairs_.append((index,next_idx))
			while (not routing.IsEnd(next_idx) ) : #while we're not at the end of the chain -  
				index = next_idx
				next_idx = assignment.Value(routing.NextVar(index))
				pairs_.append((index, next_idx))
			if pairs_[-1][-1] == len(teams):
				#this is the sentinel value, so we replace it with 0
				pairs_ = pairs_[:-1]
				pairs_.append((index,0)) #and close the loop
			#half of these pairs are hopefully the zero-length matches from previous match, so
			#print pairs_
			if fullwidth == False:
				pairs = [p for p in pairs_ if Distance(p[0],p[1]) != 0] #remove any zero weight pairs, which should *only* be the previous matches
			else:
				pairs = [p for p in pairs_]
			#check len pairs is len(teams)/2 
			#if len(pairs) != len(teams)/2:
			#	#oh no!
			#	print "length of pairs not expected!"
			#	print pairs
			#	sys.exit(33)
			for p in pairs: #and make our pair dests
				pair_dests[p[0]] = p[1]
				if fullwidth == False:
					pair_dests[p[1]] = p[0]
	#remove the new opponent from the eligible opponents list for next time
	if fullwidth == True:
		for p in pair_dests:
			pp = pair_dests[p]
			if pp in teams[p]['eligible_opponents']:
				teams[p]['eligible_opponents'].remove(pp)
				teams[p]['prev_opponents'].append(pp)
			if p in teams[pp]['eligible_opponents']:
				teams[pp]['eligible_opponents'].remove(p)
				teams[pp]['prev_opponents'].append(p)
			                       #remove all desires satisfied by p
                        if p in top8:
                                teams[pp]['desires_wt'] = -1 #actively suppress adjacent top8 games for any team
			elif teams[pp]['desires_wt'] > 0:
				teams[pp]['desires_wt'] *= 2
			if pp in top8:
				teams[p]['desires_wt'] = -1
			elif teams[p]['desires_wt'] > 0:
                        	teams[p]['desires_wt'] *= 2 #and multiply up the desire if it isn't 0
	else:	
		for p,t in zip(pair_dests,teams):
			if (p==-1): #no match
				continue
			if (p not in t['prev_opponents']):
				try:
					t['eligible_opponents'].remove(p)
					t['prev_opponents'].append(p) #and add to previous opponents list
				except:
					print "Failure to remove item: {0} (from {1})".format(p, t['name'])
					#sys.exit(1)
			#remove all desires satisfied by p
			if p in top8:
				#t['desires_wt'] = -2 #actively suppress multiple top8 matches for a team
				#try just removing all the top8s
				t['desires_wt'] = 0
				for ii in top8:
					#print ii
					#print t['eligible_opponents']
					try:
						t['eligible_opponents'].remove(ii) #remove all top8 teams as potential matches	
					except:
						pass
					try:
						teams[ii]['eligible_opponents'].remove(lookup[t['name']]) #must be mutual!
					except:
						pass
				#print t['eligible_opponents']
			elif t['desires_wt'] > 0:
				t['desires_wt'] *= 1 #and multiply up the desire if it isn't 0	

	#and process the pairs as actual pairs (remove duplication, and present as duples)
	pairs = []
	if output:
		for p,i in zip(pair_dests, range(len(teams))):
			if fullwidth == False: #list not symmetric in fullwidth
				if p < i: #already did this one
					continue
			pairs.append((i,p))
			print teams[i]['name'] + ' vs ' + teams[p]['name'] + '\n'
		#return pairs for this round [side-effect: teams are modified]
		return pairs

#TEST here (amalfi dist 4)

#eg for 6 round version, with Fontes pairs 
pair_round(teams,0, False, True)
print " "
print "R 2"
pair_round(teams,0, True, True, True) #need this for ratings to be possible

## Day 2 + 3
#calc_rating()
#print pair_round(teams,1,False, False)
#print pair_round(teams,0,True, True, True)

## Day 3.X , 4
#calc_rating()
#seed bracket


#round pairing should:

#round 1 - ignore Amalfi weights, unless we have some test ones to use
#round 2 - add additional connectivity constraint (need loop here)
#round 3+  - "standard" approach as here
