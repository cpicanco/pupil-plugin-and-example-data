# gaze-data correction via quantile-based cloud center

xLimit <- c(0, 1)
yLimit <- c(0, 1)

# with a 30-Hz frame rate, block of 1000 frames = about 33 s = about half-min
blockSize <- 1000

anchorQuantiles <- c(5, 10, 15, 85, 90, 95)/100

getOnScreenData <- function(gazeData) {
    totalAll <- nrow(gazeData)
    cat('There were', totalAll, 'raw data points.\n')
    xIsOnScreen <- xLimit[1] <= gazeData$x_norm & gazeData$x_norm <= xLimit[2]
    yIsOnScreen <- yLimit[1] <= gazeData$y_norm & gazeData$y_norm <= yLimit[2]
    onScreenData <- gazeData[xIsOnScreen & yIsOnScreen, ]
    totalOnScreen <- nrow(onScreenData)
    if (totalOnScreen < totalAll) {
        cat(totalAll - totalOnScreen, 'off-screen point(s) were discarded.\n')
    }
    onScreenData
}

oneDataBlock <- function(blockHead, gazeData) {
    blockTail <- blockHead + blockSize - 1
    lastRow <- nrow(gazeData)
    if (blockTail > lastRow) {blockTail <- lastRow}
    rowIndex <- 1:lastRow
    gazeData[blockHead <= rowIndex & rowIndex <= blockTail, ]
}

oneCloudCenter <- function(dataBlock) {
    xQuantiles <- quantile(dataBlock$x_norm, probs = anchorQuantiles)
    yQuantiles <- quantile(dataBlock$y_norm, probs = anchorQuantiles)
    c(mean(xQuantiles), mean(yQuantiles))
}

getCloudCenters <- function(gazeData) {
    blockStarters <- seq(1, nrow(gazeData), by = blockSize)
    dataBlocks <- lapply(blockStarters, oneDataBlock, gazeData)
    cloudCenters <- t(sapply(dataBlocks, oneCloudCenter))
    colnames(cloudCenters) <- c('x', 'y')
    cloudCenters
}

oneCorrectedBlock <- function(dataBlock) {
    cloudCenter <- oneCloudCenter(dataBlock)
    xCenter <- cloudCenter[1]
    xCenterReference <- 0.5
    dataBlock$x_norm <- dataBlock$x_norm + xCenterReference - xCenter
    yCenter <- cloudCenter[2]
    yCenterReference <- 0.5
    dataBlock$y_norm <- dataBlock$y_norm + yCenterReference - yCenter
    dataBlock
}

getCorrectedData <- function(gazeData) {
    blockStarters <- seq(1, nrow(gazeData), by = blockSize)
    dataBlocks <- lapply(blockStarters, oneDataBlock, gazeData)
    correctedBlocks <- lapply(dataBlocks, oneCorrectedBlock)
    do.call(rbind, correctedBlocks)
}

