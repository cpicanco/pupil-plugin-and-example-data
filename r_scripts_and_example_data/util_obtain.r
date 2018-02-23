# generic data loading and data obtention

epochsPerCycle <- 4
expectedFullCycles <- 9

minimalEpochCount <- epochsPerCycle * expectedFullCycles
minimalEpochMarks <- minimalEpochCount + 1

expandFilename <- function(subject, phase, label) {
    subject <- paste0('p', subject)
    phase <- paste0(subject, '_', phase)
    branch <- paste0(subject, '/', phase)
    paste0(branch, '/', label)
}

loadEventData <- function(subject, phase) {
    fullFilename <- expandFilename(subject, phase, 'events.dat')
    read.table(fullFilename, header = TRUE)
}

loadGazeData <- function(subject, phase) {
    fullFilename <- expandFilename(subject, phase, 'gaze.dat')
    read.table(fullFilename, header = TRUE)
}

getEpochMarks <- function(eventData) {
    allEpochMarks <- eventData[eventData$event_type == 'stimulus', ]
    if (nrow(allEpochMarks) < minimalEpochMarks) {
        return(NULL)
    }
    epochMarks <- allEpochMarks[1:minimalEpochMarks, ]
    discardedEpochs <- nrow(allEpochMarks) - minimalEpochMarks
    cat('Discarded components:', discardedEpochs, '\n')
    return(epochMarks)
}

cutBlocks <- function(targetData, epochMarks) {
    markedBlocks <- NULL
    totalMarks <- nrow(epochMarks)
    starterIndices <- 1:(totalMarks - 1)
    for (index in starterIndices) {
        timeHead <- epochMarks$time[index]
        timeTail <- epochMarks$time[index + 1]
        dataTimeOk <- timeHead <= targetData$time & targetData$time < timeTail
        extractedBlock <- targetData[dataTimeOk, ]
        markedBlocks[[index]] <- extractedBlock
    }
    markedBlocks
}

