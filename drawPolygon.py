import lakes
import matplotlib.lines as lines
from matplotlib import pyplot as plt


lakesDict = dict()
filename = "./MN_LAKES_400.txt"
lakesDict = lakes.readLakes(filename)

print lakesDict.keys()
drawingSet = [11354, 2604, 2524, 2902, 11234, 7480, 7798]
drawingSet = [226]
for lakeid in drawingSet:
	fig, ax = plt.subplots()
	polygon = lakesDict[lakeid]
	for i in range(len(polygon)-1):
		line = [tuple(polygon[i]), tuple(polygon[i+1])]
		(line_xs, line_ys) = zip(*line)
		ax.add_line(plt.Line2D(line_xs, line_ys, linewidth=2, color='blue'))
	plt.plot()
	plt.show()

for lakeid in drawingSet:
	polygon = lakesDict[lakeid]
	for i in range(len(polygon)-1):
		print polygon[i], polygon[i+1]
	raw_input()