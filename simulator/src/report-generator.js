const fs = require("fs")
const path = require("path")
const { createObjectCsvWriter } = require("csv-writer")

function generateReport(results, kpis) {
  const report = {
    metadata: {
      scenario: results.scenario,
      generatedAt: new Date().toISOString(),
      simulationDuration: results.summary.simulationDuration,
      totalTrains: results.summary.totalTrains,
    },
    kpis,
    summary: results.summary,
    analysis: generateAnalysis(results, kpis),
    recommendations: generateRecommendations(results, kpis),
    charts: generateChartData(results),
    rawData: {
      trainEvents: results.trainEvents.length,
      conflicts: results.conflicts.length,
      trackUtilization: results.trackUtilization.length,
    },
  }

  return report
}

function generateAnalysis(results, kpis) {
  const analysis = {
    performance: {
      onTimePerformance: kpis.onTimePerformance,
      averageDelay: kpis.averageDelay,
      delayDistribution: analyzeDelayDistribution(results.trainEvents),
      throughput: kpis.throughput,
    },
    efficiency: {
      trackUtilization: analyzeTrackUtilization(results.trackUtilization),
      fuelEfficiency: analyzeFuelEfficiency(results),
      passengerSatisfaction: calculatePassengerSatisfaction(kpis),
    },
    reliability: {
      conflictRate: (kpis.conflictsDetected / results.summary.totalTrains) * 100,
      incidentImpact: analyzeIncidentImpact(results.trainEvents),
      systemResilience: calculateSystemResilience(results),
    },
    capacity: {
      peakHourAnalysis: analyzePeakHours(results.trainEvents),
      bottleneckIdentification: identifyBottlenecks(results.trackUtilization),
      capacityUtilization: calculateCapacityUtilization(results),
    },
  }

  return analysis
}

function analyzeDelayDistribution(trainEvents) {
  const delays = trainEvents.filter((e) => e.type === "delay").map((e) => e.delay_minutes)

  if (delays.length === 0) {
    return { "0-5min": 0, "5-15min": 0, "15-30min": 0, "30-60min": 0, "60+min": 0 }
  }

  return {
    "0-5min": delays.filter((d) => d <= 5).length,
    "5-15min": delays.filter((d) => d > 5 && d <= 15).length,
    "15-30min": delays.filter((d) => d > 15 && d <= 30).length,
    "30-60min": delays.filter((d) => d > 30 && d <= 60).length,
    "60+min": delays.filter((d) => d > 60).length,
  }
}

function analyzeTrackUtilization(trackUtilization) {
  if (!trackUtilization || trackUtilization.length === 0) {
    return { average: 0, peak: 0, underutilized: [], overutilized: [] }
  }

  const utilizationRates = []
  const trackStats = {}

  trackUtilization.forEach((snapshot) => {
    Object.entries(snapshot).forEach(([trackId, data]) => {
      if (!trackStats[trackId]) {
        trackStats[trackId] = []
      }
      trackStats[trackId].push(data.occupancy_rate)
      utilizationRates.push(data.occupancy_rate)
    })
  })

  const averageUtilization = utilizationRates.reduce((sum, rate) => sum + rate, 0) / utilizationRates.length
  const peakUtilization = Math.max(...utilizationRates)

  const underutilized = []
  const overutilized = []

  Object.entries(trackStats).forEach(([trackId, rates]) => {
    const avgRate = rates.reduce((sum, rate) => sum + rate, 0) / rates.length
    if (avgRate < 0.3) {
      underutilized.push({ trackId, utilization: avgRate })
    } else if (avgRate > 0.8) {
      overutilized.push({ trackId, utilization: avgRate })
    }
  })

  return {
    average: averageUtilization,
    peak: peakUtilization,
    underutilized,
    overutilized,
  }
}

function analyzeFuelEfficiency(results) {
  if (!results.summary.totalFuelConsumed || !results.summary.totalDistance) {
    return { efficiency: 0, totalConsumed: 0, averagePerKm: 0 }
  }

  return {
    efficiency: results.summary.totalDistance / results.summary.totalFuelConsumed, // km per liter
    totalConsumed: results.summary.totalFuelConsumed,
    averagePerKm: results.summary.totalFuelConsumed / results.summary.totalDistance,
  }
}

function calculatePassengerSatisfaction(kpis) {
  // Simplified passenger satisfaction based on delays and on-time performance
  let satisfaction = 100

  // Reduce satisfaction based on average delay
  satisfaction -= Math.min(kpis.averageDelay * 2, 50) // Max 50 point reduction

  // Adjust based on on-time performance
  satisfaction = satisfaction * (kpis.onTimePerformance / 100)

  return Math.max(0, Math.min(100, satisfaction))
}

function analyzeIncidentImpact(trainEvents) {
  const incidentEvents = trainEvents.filter((e) => e.type.includes("incident"))

  const impactByType = {}
  let totalDelayFromIncidents = 0

  incidentEvents.forEach((event) => {
    const type = event.incident_type || "unknown"
    if (!impactByType[type]) {
      impactByType[type] = { count: 0, totalDelay: 0, affectedTrains: new Set() }
    }

    impactByType[type].count++
    impactByType[type].totalDelay += event.delay_minutes || 0
    impactByType[type].affectedTrains.add(event.train_id)
    totalDelayFromIncidents += event.delay_minutes || 0
  })

  // Convert sets to counts
  Object.values(impactByType).forEach((impact) => {
    impact.affectedTrains = impact.affectedTrains.size
  })

  return {
    totalIncidents: incidentEvents.length,
    totalDelayFromIncidents,
    impactByType,
    averageDelayPerIncident: incidentEvents.length > 0 ? totalDelayFromIncidents / incidentEvents.length : 0,
  }
}

function calculateSystemResilience(results) {
  const totalTrains = results.summary.totalTrains
  const completedTrains = results.summary.completedTrains
  const conflictsDetected = results.summary.conflictsDetected || 0

  // Resilience score based on completion rate and conflict handling
  const completionRate = completedTrains / totalTrains
  const conflictRate = conflictsDetected / totalTrains

  // Higher completion rate and lower conflict rate = higher resilience
  const resilienceScore = (completionRate * 0.7 + (1 - Math.min(conflictRate, 1)) * 0.3) * 100

  return {
    score: Math.max(0, Math.min(100, resilienceScore)),
    completionRate: completionRate * 100,
    conflictRate: conflictRate * 100,
    factors: {
      completion: completionRate >= 0.9 ? "excellent" : completionRate >= 0.7 ? "good" : "poor",
      conflicts: conflictRate <= 0.1 ? "low" : conflictRate <= 0.3 ? "moderate" : "high",
    },
  }
}

function analyzePeakHours(trainEvents) {
  const hourlyActivity = {}

  trainEvents.forEach((event) => {
    const hour = new Date(event.timestamp).getHours()
    if (!hourlyActivity[hour]) {
      hourlyActivity[hour] = 0
    }
    hourlyActivity[hour]++
  })

  const sortedHours = Object.entries(hourlyActivity)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)

  return {
    peakHours: sortedHours.map(([hour, activity]) => ({ hour: Number.parseInt(hour), activity })),
    hourlyDistribution: hourlyActivity,
  }
}

function identifyBottlenecks(trackUtilization) {
  if (!trackUtilization || trackUtilization.length === 0) {
    return []
  }

  const trackAverages = {}

  trackUtilization.forEach((snapshot) => {
    Object.entries(snapshot).forEach(([trackId, data]) => {
      if (!trackAverages[trackId]) {
        trackAverages[trackId] = { total: 0, count: 0, conflicts: 0 }
      }
      trackAverages[trackId].total += data.occupancy_rate
      trackAverages[trackId].count++
      if (data.occupancy_rate > 0.9) {
        trackAverages[trackId].conflicts++
      }
    })
  })

  const bottlenecks = Object.entries(trackAverages)
    .map(([trackId, stats]) => ({
      trackId,
      averageUtilization: stats.total / stats.count,
      conflictFrequency: stats.conflicts / stats.count,
      severity: (stats.total / stats.count + stats.conflicts / stats.count) / 2,
    }))
    .filter((track) => track.severity > 0.7)
    .sort((a, b) => b.severity - a.severity)

  return bottlenecks
}

function calculateCapacityUtilization(results) {
  const totalCapacity = results.summary.totalTrains * 100 // Assume 100% is full capacity
  const actualThroughput = results.summary.completedTrains

  return {
    utilizationRate: (actualThroughput / totalCapacity) * 100,
    remainingCapacity: totalCapacity - actualThroughput,
    efficiency: actualThroughput / results.summary.totalTrains,
  }
}

function generateRecommendations(results, kpis) {
  const recommendations = []

  // Performance recommendations
  if (kpis.onTimePerformance < 80) {
    recommendations.push({
      category: "Performance",
      priority: "High",
      issue: "Low on-time performance",
      recommendation: "Implement dynamic scheduling and increase buffer times between trains",
      expectedImpact: "15-20% improvement in on-time performance",
    })
  }

  if (kpis.averageDelay > 15) {
    recommendations.push({
      category: "Performance",
      priority: "High",
      issue: "High average delays",
      recommendation: "Review timetable feasibility and add recovery time at key stations",
      expectedImpact: "Reduce average delays by 30-40%",
    })
  }

  // Capacity recommendations
  const analysis = generateAnalysis(results, kpis)
  if (analysis.capacity.bottleneckIdentification.length > 0) {
    recommendations.push({
      category: "Capacity",
      priority: "Medium",
      issue: "Track bottlenecks identified",
      recommendation: "Consider track capacity expansion or improved signaling at bottleneck locations",
      expectedImpact: "Increase overall system throughput by 10-15%",
    })
  }

  // Efficiency recommendations
  if (analysis.efficiency.trackUtilization.average < 0.5) {
    recommendations.push({
      category: "Efficiency",
      priority: "Low",
      issue: "Low track utilization",
      recommendation: "Optimize train scheduling to better utilize available track capacity",
      expectedImpact: "Improve resource utilization and reduce operational costs",
    })
  }

  // Reliability recommendations
  if (analysis.reliability.conflictRate > 20) {
    recommendations.push({
      category: "Reliability",
      priority: "High",
      issue: "High conflict rate",
      recommendation: "Implement advanced conflict detection and resolution algorithms",
      expectedImpact: "Reduce conflicts by 50-60%",
    })
  }

  return recommendations
}

function generateChartData(results) {
  return {
    delayTrend: generateDelayTrendData(results.trainEvents),
    trackUtilization: generateTrackUtilizationData(results.trackUtilization),
    hourlyActivity: generateHourlyActivityData(results.trainEvents),
    conflictsByType: generateConflictsByTypeData(results.conflicts),
    performanceMetrics: generatePerformanceMetricsData(results),
  }
}

function generateDelayTrendData(trainEvents) {
  const delayEvents = trainEvents.filter((e) => e.type === "delay" || e.delay_minutes > 0)

  const hourlyDelays = {}
  delayEvents.forEach((event) => {
    const hour = new Date(event.timestamp).getHours()
    if (!hourlyDelays[hour]) {
      hourlyDelays[hour] = { total: 0, count: 0 }
    }
    hourlyDelays[hour].total += event.delay_minutes || 0
    hourlyDelays[hour].count++
  })

  return Object.entries(hourlyDelays).map(([hour, data]) => ({
    hour: Number.parseInt(hour),
    averageDelay: data.total / data.count,
    totalDelay: data.total,
    incidents: data.count,
  }))
}

function generateTrackUtilizationData(trackUtilization) {
  if (!trackUtilization || trackUtilization.length === 0) {
    return []
  }

  const utilizationData = []
  trackUtilization.forEach((snapshot, index) => {
    const avgUtilization =
      Object.values(snapshot).reduce((sum, data) => sum + data.occupancy_rate, 0) / Object.keys(snapshot).length

    utilizationData.push({
      timeStep: index,
      averageUtilization: avgUtilization,
      peakUtilization: Math.max(...Object.values(snapshot).map((data) => data.occupancy_rate)),
    })
  })

  return utilizationData
}

function generateHourlyActivityData(trainEvents) {
  const hourlyActivity = {}

  trainEvents.forEach((event) => {
    const hour = new Date(event.timestamp).getHours()
    const type = event.type

    if (!hourlyActivity[hour]) {
      hourlyActivity[hour] = {}
    }
    if (!hourlyActivity[hour][type]) {
      hourlyActivity[hour][type] = 0
    }
    hourlyActivity[hour][type]++
  })

  return Object.entries(hourlyActivity).map(([hour, activities]) => ({
    hour: Number.parseInt(hour),
    ...activities,
  }))
}

function generateConflictsByTypeData(conflicts) {
  const conflictsByType = {}

  conflicts.forEach((conflict) => {
    const type = conflict.type
    if (!conflictsByType[type]) {
      conflictsByType[type] = { count: 0, severity: [] }
    }
    conflictsByType[type].count++
    conflictsByType[type].severity.push(conflict.severity === "high" ? 3 : conflict.severity === "medium" ? 2 : 1)
  })

  return Object.entries(conflictsByType).map(([type, data]) => ({
    type,
    count: data.count,
    averageSeverity: data.severity.reduce((sum, s) => sum + s, 0) / data.severity.length,
  }))
}

function generatePerformanceMetricsData(results) {
  return {
    onTimePerformance: results.summary.onTimePerformance,
    averageDelay: results.summary.averageDelay,
    throughput: results.summary.completedTrains,
    fuelEfficiency: results.summary.averageFuelConsumption,
    passengerSatisfaction: calculatePassengerSatisfaction({
      averageDelay: results.summary.averageDelay,
      onTimePerformance: results.summary.onTimePerformance,
    }),
  }
}

async function exportToCSV(results, filename) {
  const csvWriter = createObjectCsvWriter({
    path: filename,
    header: [
      { id: "timestamp", title: "Timestamp" },
      { id: "train_id", title: "Train ID" },
      { id: "event_type", title: "Event Type" },
      { id: "station", title: "Station" },
      { id: "delay_minutes", title: "Delay (minutes)" },
      { id: "scheduled_time", title: "Scheduled Time" },
      { id: "actual_time", title: "Actual Time" },
    ],
  })

  const records = results.trainEvents.map((event) => ({
    timestamp: event.timestamp,
    train_id: event.train_id,
    event_type: event.type,
    station: event.station || "",
    delay_minutes: event.delay_minutes || 0,
    scheduled_time: event.scheduled_time ? new Date(event.scheduled_time * 1000).toISOString() : "",
    actual_time: event.actual_time ? new Date(event.actual_time * 1000).toISOString() : "",
  }))

  await csvWriter.writeRecords(records)
}

module.exports = {
  generateReport,
  exportToCSV,
  generateAnalysis,
  generateRecommendations,
}
