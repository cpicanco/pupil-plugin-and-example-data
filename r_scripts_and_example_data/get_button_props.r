# analyze button-pressing proportions

subject <- readline('Subject (1..8)? ')
phase <- readline('Phase (1, 2, 3)? ')

source('util_obtain.r')

eventData <- loadEventData(subject, phase)

responseEvents <- eventData[eventData$event_type == 'response', ]

epochMarks <- getEpochMarks(eventData)
if (is.null(epochMarks)) {
    halt('Not enough components to proceed.')
}

dataBlocks <- cutBlocks(responseEvents, epochMarks)
cycleCount <- length(dataBlocks)/epochsPerCycle
cat('Cycle count:', cycleCount, '\n')

responseCounts <- sapply(dataBlocks, nrow)

totalEpochPairs <- length(responseCounts) %/% 2
epochPairIndices <- rep(1:totalEpochPairs, each = 2)

responsesPerEpochPair <- by(responseCounts, INDICES = epochPairIndices, sum)
responsesPerEpochPair <- as.vector(responsesPerEpochPair)

redBlue <- c('red', 'blue')
totalRedBlue <- length(responsesPerEpochPair) %/% 2
redBlueFrame <- rep(redBlue, times = totalRedBlue)

responsesInRed <- responsesPerEpochPair[redBlueFrame == 'red']
responsesInBlue <- responsesPerEpochPair[redBlueFrame == 'blue']

responseProp <- responsesInRed/(responsesInRed + responsesInBlue)
writeLines('Response proportions along four-component blocks:')
print(responseProp)

