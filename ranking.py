import random
import math
import statsmodels.api as sm
import numpy as np
#team dict
#
# strength = "some numerical measure of the (true) team strength
#
#

#upperbound log 2
def ceillog2(x):
	return math.ceil(math.log(x)/math.log(2))

#a safe approx to ratio
def saferatio(x,y):
	if x==0:
		x = 0.5
	if y==0:
		y = 0.5
	return float(x)/y

def update_rankings(teams, result_rounds, wl=1,ss=0.1, massey=-1):
	#various kinds of updates - win/loss, score_share, etc
	tmp_wl = {t['name']:0 for t in teams}
	if wl > 0:
		for rr in result_rounds:
			for r in rr:
				vals = win_loss(r[0],r[1])
				tmp_wl[r[0]['name']]+= vals[0]
				tmp_wl[r[1]['name']]+= vals[1]
	tmp_ss = {t['name']:0 for t in teams}
	if ss > 0: 
                for rr in result_rounds:
                        for r in rr:
                                vals = score_share(r[0],r[1])
                                tmp_ss[r[0]['name']]+= vals[0]
                                tmp_ss[r[1]['name']]+= vals[1]
	#LeagueVine uses Massey ratings as "Power Rankings" for Swiss tournaments in Ultimate Frisbee!
	
	tmp_massey = {t['name']:0 for t in teams}
	if massey > 0:	
		tot_cols = sum([len(rr) for rr in result_rounds]) #total number of results
		tot_rows = len(teams)
		#indexing function, maps teamnames to row
		idx = { i[0]['name']:i[1] for i in zip(teams,range(len(teams)))}
		col = 0
		A = np.zeros([tot_cols,tot_rows])
		Y = np.zeros(tot_cols)
		for rr in result_rounds:
			for r in rr:
				#make A, Y matrices
				A[col][idx[r[0]['name']]] = 1
				A[col][idx[r[1]['name']]] = -1
				Y[col] = math.log(saferatio(r[0]['score'],r[1]['score'])) 		
				col += 1
		#and solve by least squares for B
		#tmp_massey = lsqrssolve(A,Y)
		res = sm.OLS(Y,A).fit() #L2 regression
		#res = sm.QuantReg(Y,A).fit(q=0.5) #L1 regression
		#res = sm.OLS(Y,A).fit_regularized(L1_wt=1.0) #Lasso (L2 w/ L1 reg)
		for t,p in zip(teams,res.params):
			tmp_massey[t['name']] = p
		#res.params => tmp_massey values, in the same ordering, I think
	tmp_ratings = { t['name']:wl*tmp_wl[t['name']]+ss*tmp_ss[t['name']]+massey*tmp_massey[t['name']] for t in teams}
	#some combination above, gives us tmp_rankings
	for t in teams:
		t['oldrating']=t['rating'] #for fontes ranks
		t['rating'] = tmp_ratings[t['name']]


