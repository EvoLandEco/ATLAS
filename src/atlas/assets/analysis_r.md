# Run from the extracted dataset directory: Rscript analysis.R
metrics <- read.csv("event_metrics.csv", na.strings="N/A", stringsAsFactors=FALSE,
                    check.names=FALSE)
observations <- read.csv("observations.csv", na.strings="N/A", stringsAsFactors=FALSE,
                         check.names=FALSE)
selected <- subset(metrics, metric == "cases" & value_status == "reported")
print(selected[c("event_id", "count_kind", "value", "unit", "period_end")])
# read.csv's explicit N/A sentinel preserves country code NA for Namibia.
# Each cumulative series is a scoped snapshot; count changes retain their reporting-change label.
