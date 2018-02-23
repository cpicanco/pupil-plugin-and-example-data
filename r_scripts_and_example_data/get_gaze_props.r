# analyze gaze proportions along schedule components

subject <- readline('Subject (1..8)? ')
phase <- readline('Phase (1, 2, 3)? ')

source('util_obtain.r')
source('util_correct.r')

gazeData <- loadGazeData(subject, phase)
onScreenData <- getOnScreenData(gazeData)
correctedData <- getCorrectedData(onScreenData)

eventData <- loadEventData(subject, phase)

epochMarks <- getEpochMarks(eventData)
if (is.null(epochMarks)) {
    halt('Not enough components to proceed.')
}

dataBlocks <- cutBlocks(correctedData, epochMarks)

epochDurations <- diff(epochMarks$time)
totalEpochs <- length(epochDurations)
cat('Total components:', totalEpochs, '\n')

# classify each recorded gaze

leftSpot <- c(0.334, 0.497)
rightSpot <- c(0.667, 0.497)

centerToCenter <- 0.334
toleranceRadius <- centerToCenter/2

distance <- function(block, landmark) {
    x <- block$x_norm
    y <- block$y_norm
    sumSquareDevs <- (x - landmark[1])^2 + (y - landmark[2])^2
    sqrt(sumSquareDevs)
}

oneClassifiedBlock <- function(block) {
    left <- distance(block, leftSpot) <= toleranceRadius
    right <- distance(block, rightSpot) <= toleranceRadius
    classifiedBlock <- ifelse(left, 'L', ifelse(right, 'R', 'X'))
    factor(classifiedBlock, levels = c('L', 'R', 'X'))
}

classifiedBlocks <- lapply(dataBlocks, oneClassifiedBlock)

# analyze switching rates

oneSwitchingCount <- function(classifiedBlock) {
    purifiedBlock <- classifiedBlock[classifiedBlock != 'X']
    leftRightCodes <- as.numeric(purifiedBlock)
    leftRightChanges <- diff(leftRightCodes)
    sum(leftRightChanges != 0)
}

switchingCounts <- sapply(classifiedBlocks, oneSwitchingCount)
switchingRates <- switchingCounts/epochDurations

totalEpochPairs <- length(epochDurations) %/% 2
epochPairIndices <- rep(1:totalEpochPairs, each = 2)

switchingPerEpochPair <- by(switchingRates, INDICES = epochPairIndices, mean)
switchingPerEpochPair <- as.vector(switchingPerEpochPair)

redBlue <- c('red', 'blue')
totalRedBlue <- totalEpochPairs %/% 2
redBlueFrame <- rep(redBlue, times = totalRedBlue)

switchingInRed <- switchingPerEpochPair[redBlueFrame == 'red']
switchingInBlue <- switchingPerEpochPair[redBlueFrame == 'blue']

switching <- data.frame(switchingInRed, switchingInBlue)
writeLines('')
print(switching)

switchingDifferential <- mean(switchingInBlue) - mean(switchingInRed)
writeLines('')
cat('Switching differential:', switchingDifferential, '\n')

# analyze gaze proportions

gazeCounts <- t(sapply(classifiedBlocks, table))
gazeProps <- gazeCounts[ , 'L']/(gazeCounts[ , 'L'] + gazeCounts[ , 'R'])

writeLines('')
writeLines('Left props along components:')
print(gazeProps)

stimulusChangeOnLeft <- seq(from = 3, to = totalEpochs, by = 2)
stimulusChangeOnRight <- seq(from = 2, to = totalEpochs, by = 2)

gazePropsOnLeftChange <- gazeProps[stimulusChangeOnLeft]
writeLines('')
writeLines('Left props on left change:')
print(gazePropsOnLeftChange)

gazePropsOnRightChange <- gazeProps[stimulusChangeOnRight]
writeLines('')
writeLines('Left props on right change:')
print(gazePropsOnRightChange)

trackingIndex <- mean(gazePropsOnLeftChange) - mean(gazePropsOnRightChange)
writeLines('')
writeLines('Tracking index=')
print(trackingIndex)

propsPerEpochPair <- by(gazeProps, INDICES = epochPairIndices, mean)
propsPerEpochPair <- as.vector(propsPerEpochPair)

propsInRed <- propsPerEpochPair[redBlueFrame == 'red']
propsInBlue <- propsPerEpochPair[redBlueFrame == 'blue']

props <- data.frame(propsInRed, propsInBlue)
writeLines('')
print(props)

