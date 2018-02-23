# check gaze drift dynamics via cloud-center estimation

subject <- readline('Subject (1..8)? ')
phase <- readline('Phase (1, 2, 3)? ')

source('util_obtain.r')

gazeData <- loadGazeData(subject, phase)

source('util_correct.r')

onScreenData <- getOnScreenData(gazeData)
plot(
    onScreenData$x_norm, onScreenData$y_norm,
    xlim = c(0, 1), ylim = c(0, 1), cex = 0.1, col = 'red'
)

cloudCenters <- getCloudCenters(onScreenData)
cat('Successive cloud centers:', '\n')
print(cloudCenters)

correctedData <- getCorrectedData(onScreenData)
points(
    correctedData$x_norm, correctedData$y_norm,
    xlim = c(0, 1), ylim = c(0, 1), cex = 0.1, col = 'blue'
)

xLeftSpot <- 0.3335
xRightSpot <- 0.667

yBothSpots <- 0.497

abline(v = xLeftSpot, lty = 'dashed')
abline(v = xRightSpot, lty = 'dashed')

abline(h = yBothSpots, lty = 'dashed')

