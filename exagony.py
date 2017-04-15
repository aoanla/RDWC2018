

teamnames = ["Indigenous","Argentina","Australia","Belgium","Brazil","Canada","Chile","Colombia","Denmark","England","Finland","France","Germany","Greece","Ireland","Italy","Japan","Mexico","Netherlands","New Zealand","Norway","Portugal","Puerto Rico","Scotland","South Africa","Spain","Sweden","Switzerland","Wales","West Indies","United States","Korea","Iceland","Philippines","Romania","Czech Republic","Costa Rica","Iran","Russia","Austria"]

#adjacencies
adj = {}

for i in teamnames:
	adj[i] = []

pairs = [("Argentina","Chile"),
("Argentina","Brazil"),
("Australia","New Zealand"),
("United States","Canada"),
("United States","Mexico"),
("United States","Korea"),
("United States","Puerto Rico"),
("Belgium","France"),
("Belgium","Netherlands"),
("Belgium","Germany"),
("Brazil","Colombia"),
("Chile","Colombia"),
("Colombia","Costa Rica"),
("Colombia","Mexico"),
("Denmark","Germany"),
("Denmark","Norway"),
("Denmark","Sweden"),
("England","Scotland"),
("England","Wales"),
("England","Ireland"),
("England","France"),
("England","West Indies"),
("Finland","Russia"),
("Finland","Sweden"),
("Finland","Norway"),
("France","Germany"),
("France","Spain"),
("France","Italy"),
("France","Switzerland"),
("Germany","Austria"),
("Germany","Switzerland"),
("Germany","Czech Republic"),
("Germany","Netherlands"),
("Germany","Sweden"),
("Greece","Italy"),
("Greece","Romania"),
("Ireland","Scotland"),
("Ireland","Wales"),
("Italy","Austria"),
("Italy","Switzerland"),
("Japan","Australia"),
("Japan","New Zealand"),
("Mexico","Costa Rica"),
("Norway","Sweden"),
("Portugal","Spain"),
("Scotland","Wales"),
("Sweden","Russia"),
("Switzerland","Austria")]

#add pairs (adjacency is symmetric)
for i in pairs: 
	adj[i[0]].append(i[1])
	adj[i[1]].append(i[0])


regionmask = 0x0
masks = { i:0x0 for i in teamnames}

#LA mask = 0x1
for i in ["Argentina","Brazil","Chile","Colombia","Mexico", "Costa Rica"]:
	masks[i] = masks[i] | 0x1

#NA mask = 0x2
for i in ["United States", "Korea", "Canada", "Mexico", "Puerto Rico", "Costa Rica", "Philippines"]:
	masks[i] = masks[i] | 0x2

#EURO mask = 0x4
for i in ["Belgium","Denmark","England","Finland","France","Germany","Greece","Ireland","Italy","Netherlands","Norway","Portugal","Scotland","Spain","Sweden","Switzerland","Wales","Iceland","Romania","Czech Republic","Russia","Austria"]:
	masks[i] = masks[i] | 0x4

#PACIFIC mask = 0x8
for i in ["Australia","New Zealand","Japan"]:
	masks[i] = masks[i] | 0x8

#INDIG mask = 0xF
#for i in ["Indigenous","USA","Canada","Australia","New Zealand"]:
#	masks[i] = masks[i] | 0xF

#everyone else has no region

#exagony calculation
def get_exagony_dist(team1, team2):
	#teams are adjacent
	if team2 in adj[team1]:
		return 0
	#teams share a region
	if masks[team1] & masks[team2]:
		return 1
	#teams share neither adjacency or region
	return 2
