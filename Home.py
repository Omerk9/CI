import time
import timeit
from scipy import sparse
from scipy.spatial import distance_matrix
import mlrose
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# get the x,y coordinates from the file in the specific location
def openfile(location):
    x, y = [], []
    with open(location, 'r') as f:
        for l in f:
            row = l.split()
            x.append(row[0])
            y.append(row[1])
        return x, y

# return flat list of x,y coordinates (list of tuples)
def getflatlist(x, y):
    coords_list = [list(t) for t in zip(x, y)]
    length = len(x)
    print("the length of the list is:",length)
    flat_list = []
    for sublist in coords_list:
        first = float(sublist[0])
        second = float(sublist[1])
        flat_list.append((first, second))
    print("flat_list",flat_list)
    return flat_list

# return data frame of distances matrix (the distance between city a to city b for every city)
def getdistancesmatrixdf(flatlist):
    city = list(range(0, len(flatlist)))
    print("cities are:",city)
    df = pd.DataFrame(flatlist, columns=['xcord', 'ycord'], index=city)
    df2 = pd.DataFrame(distance_matrix(df.values, df.values), index=df.index, columns=df.index)
    print(len(flatlist),"city", df2)
    return df2

# return list of distances between city a to city b for every city in the data frame given
def getdistanceslistfromdf(df2):
    Row_list = []
    indexes = df2.columns
    for i in indexes:
        for j in indexes:
            if i != j:
                Row_list.append((i, j, df2[i][j]))

    print(Row_list)
    return Row_list

# return data frame of the next city, b, which we need to go from city a
def createnextcity(df):
    df.columns = ["cities"]
    df["next_city"] = df["cities"]
    for i in range(0, len(df)-1):
        if i != 0:
            df.loc[i, "next_city"] = df["cities"][(i - 1)]
    df.loc[0, "next_city"] = df["cities"][len(df)-1]
    return df

# return sparse data frame of the next cities
def createsparsedf(df):
    sparse_df = pd.DataFrame(0, index=range(0, len(df)-1), columns=range(0, len(df)-1))
    for i in range(0, len(df)):
        for j in range(0, len(df)):
            sparse_df.loc[i, j] = 0
    for i in range(0, len(df)-1):
        value1 = df["cities"][i]
        value2 = df["next_city"][i]
        sparse_df.loc[value1, value2] = 1
        sparse_df2 = sparse.csr_matrix(sparse_df)
    return sparse_df2

# create plot of the tour of cities from sparse data frame
def plotgraphfromsparsedf(df):
    G = nx.from_scipy_sparse_matrix(df)

    # Plot it
    nx.draw(G, with_labels=True)
    plt.draw()
    plt.show()

# return list of longitude and latitude of the cities from x,y coordinates list
def getcordsfromxy(flatlist):
    from pyproj import Proj, transform
    import cv2
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    x1, y1 = -11705274.6374, 4826473.6922
    x2, y2 = transform(inProj, outProj, x1, y1)
    print(x2, y2)
    flatlistcords = []
    for x1, y1 in flatlist:
        flatlistcords.append(transform(inProj, outProj, x1, y1))
    print(flatlistcords)
    return flatlistcords

# plot the tour of the algorithm by the longitude and latitude of the cities and the results data frame.
def plotonimage(dfcords,flatlistcords,title):
    BBox = ((dfcords.longitude.min(), dfcords.longitude.max(), dfcords.latitude.min(), dfcords.latitude.max()))
    print(BBox)
    ruh_m = plt.imread('C:/Users/Dvir/Downloads/qamap_194.png')
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.scatter(dfcords.longitude, dfcords.latitude, zorder=1, alpha=1, c='b', s=20)
    ax.set_title(title)
    ax.set_xlim(BBox[0], BBox[1])
    ax.set_ylim(BBox[2], BBox[3])
    for i in range(0, len(flatlistcords) - 1):
        xval = (flatlistcords[i][0], flatlistcords[i + 1][0])
        yval = (flatlistcords[i][1], flatlistcords[i + 1][1])
        plt.plot(xval, yval)
    xval = (flatlistcords[len(flatlistcords) - 1][0], flatlistcords[0][0])
    yval = (flatlistcords[len(flatlistcords) - 1][1], flatlistcords[0][1])
    plt.plot(xval, yval)
    ax.imshow(ruh_m, zorder=0, extent=BBox, aspect='equal')


def main():

    # find the optimal solution:
    x, y = openfile("C:/Users/Dvir/Downloads/att20_xy.txt")
    flatlist = getflatlist(x, y)

    flatlistcords = getcordsfromxy(flatlist)

    city = list(range(0, len(flatlistcords)))
    dfcords = pd.DataFrame(flatlistcords, columns=['longitude', 'latitude'], index=city)

    #plotonimage(dfcords, flatlistcords, "basic cities")

    df2 = getdistancesmatrixdf(flatlist)
    best_sol = list(range(0, len(flatlist)))
    sum_of_optimal_sol = 0
    for i in range(len(best_sol)-1):
        sum_of_optimal_sol = sum_of_optimal_sol + df2[best_sol[i]][best_sol[i+1]]
    sum_of_optimal_sol = sum_of_optimal_sol + df2[best_sol[len(best_sol)-1]][best_sol[0]]
    print("the optimal sol is:", sum_of_optimal_sol)

    # open the file
    #x, y = openfile("C:/Users/Dvir/Downloads/att20_xy.txt")

    x, y = openfile("C:/Users/Dvir/Downloads/xy_38.txt")
    # get flat list
    flatlist = getflatlist(x, y)
    # create distances matrix data frame from the flat list x, y coordinates
    df2 = getdistancesmatrixdf(flatlist)
    # create distances matrix list from data frame
    Row_list = getdistanceslistfromdf(df2)
    # define the coordinates of the TSP problem from "mlrose" package
    fitness_coords = mlrose.TravellingSales(distances=Row_list)
    # define the problem of TSP from "mlrose" package
    problem_fit = mlrose.TSPOpt(length=38, fitness_fn=fitness_coords, maximize=False)


    #simulated_annealing
    begin = time.time()
    best_state_simulated_annealing, best_fitness_simulated_annealing =\
        mlrose.simulated_annealing(problem_fit, max_attempts=100000, max_iters=100000, random_state=2)
    time.sleep(1)
    end = time.time()
    print(f"Total runtime of the simulated algo is {end - begin}")

    print('The best state found for simulated_annealing is: ', best_state_simulated_annealing)
    print('The fitness at the best state for simulated_annealing is: ', best_fitness_simulated_annealing)
    print("the approx of simulated is: ", best_fitness_simulated_annealing / sum_of_optimal_sol)

    flatlistofxyofresult = []
    for city in best_state_simulated_annealing:
        flatlistofxyofresult.append(flatlist[city])
    print("flatlistofxyofresult", flatlistofxyofresult)
    resultscords = getcordsfromxy(flatlistofxyofresult)
    print("resultscords", resultscords)
    city = list(range(0, len(resultscords)))
    dfcords = pd.DataFrame(resultscords, columns=['longitude', 'latitude'], index=city)
    plotonimage(dfcords, resultscords, "cities after simulated algorithm")

    best_state_df = pd.DataFrame(best_state_simulated_annealing)
    print(best_state_df)
    best_state_df = createnextcity(best_state_df)
    print("best_state_df", best_state_df)
    sparse_df = createsparsedf(best_state_df)
    plotgraphfromsparsedf(sparse_df)
    print("sparse df", sparse_df)


    fig, ax = plt.subplots(figsize=(8, 7))
    ax.scatter(dfcords.longitude, dfcords.latitude, zorder=1, alpha=1, c='r', s=8)
    ax.set_title("title")
    plt.show()


    # run genetic algorithm
    #calculate the running time of the algorithm
    begin = time.time()
    # find the best tour and the best length of the tour of the algorithm by define the max attempts and the max iteretions
    best_state_genetic, best_fitness_genetic = \
        mlrose.genetic_alg(problem_fit, max_attempts=1, max_iters=1, random_state=2)

    time.sleep(1)
    end = time.time()
    print(f"Total runtime of the genetic algo is {end - begin}")
    print('The best state found for genetic_alg is: ', best_state_genetic)
    print('The fitness at the best state for genetic_alg is: ', best_fitness_genetic)
    print("the approx of genetic is: ", best_fitness_genetic/sum_of_optimal_sol)
    # convert the result tour to data frame
    best_state_df = pd.DataFrame(best_state_genetic)
    flatlistofxyofresult = []
    # convert the x, y coordinates data frame to x, y coordinates list
    for city in best_state_genetic:
        flatlistofxyofresult.append(flatlist[city])
    print("flatlistofxyofresult",flatlistofxyofresult)
    # convert the x,y result list to long/lat coordinates list
    resultscords = getcordsfromxy(flatlistofxyofresult)
    print("resultscords",resultscords)
    city = list(range(0, len(resultscords)))
    # create log/lat coordinates data frame
    dfcords = pd.DataFrame(resultscords, columns=['longitude', 'latitude'], index=city)
    # plot the algorithm best tour from long/lat coordinates
    plotonimage(dfcords, resultscords, "cities after genetic algorithm")
    print("best_state_df",best_state_df)
    # create data frame of city 'a' to city 'b'
    best_state_df = createnextcity(best_state_df)
    print("best_state_df", best_state_df)
    # create sparse data frame of the tour
    sparse_df = createsparsedf(best_state_df)
    print("sparse df", sparse_df)
    # plot the tour
    plotgraphfromsparsedf(sparse_df)



#hill_climb
    begin = time.time()
    best_state_hill, best_fitness_hill = mlrose.hill_climb(problem_fit, max_iters=100000, random_state=2)
    time.sleep(1)
    end = time.time()
    print(f"Total runtime of the hill climb algo is {end - begin}")

    print('The best state found for hill_climb is: ', best_state_hill)
    print('The fitness at the best state for hill_climb is: ', best_fitness_hill)
    print("the approx of hill is: ", best_fitness_hill / sum_of_optimal_sol)

    flatlistofxyofresult = []
    for city in best_state_hill:
        flatlistofxyofresult.append(flatlist[city])
    print("flatlistofxyofresult", flatlistofxyofresult)
    resultscords = getcordsfromxy(flatlistofxyofresult)
    print("resultscords", resultscords)
    city = list(range(0, len(resultscords)))
    dfcords = pd.DataFrame(resultscords, columns=['longitude', 'latitude'], index=city)
    plotonimage(dfcords, resultscords, "cities after hill climb algorithm")

    best_state_df = pd.DataFrame(best_state_hill)
    print(best_state_df)
    best_state_df = createnextcity(best_state_df)
    print("best_state_df", best_state_df)
    sparse_df = createsparsedf(best_state_df)
    print("sparse df", sparse_df)
    plotgraphfromsparsedf(sparse_df)


if __name__ == '__main__':
    main()