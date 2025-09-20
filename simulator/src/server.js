const express = require("express")
const cors = require("cors")
const helmet = require("helmet")
const morgan = require("morgan")
const winston = require("winston")

const { SimulationEngine } = require("./simulation-engine")
const { generateReport } = require("./report-generator")

// Configure logging
const logger = winston.createLogger({
  level: "info",
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  transports: [new winston.transports.Console(), new winston.transports.File({ filename: "simulator.log" })],
})

const app = express()
const port = process.env.PORT || 8002

// Middleware
app.use(helmet())
app.use(cors())
app.use(morgan("combined"))
app.use(express.json({ limit: "10mb" }))

// Initialize simulation engine
const simulationEngine = new SimulationEngine()

// Routes
app.get("/", (req, res) => {
  res.json({
    message: "RailOptima Simulation Service",
    version: "1.0.0",
    endpoints: ["/simulate", "/health"],
  })
})

app.post("/simulate", async (req, res) => {
  try {
    const { scenario, timetable, incidents, duration_minutes = 240, time_step_seconds = 60 } = req.body

    logger.info(`Starting simulation: ${scenario.name || "Unnamed"}`)

    // Run simulation
    const results = await simulationEngine.runSimulation({
      scenario,
      timetable,
      incidents,
      duration_minutes,
      time_step_seconds,
    })

    // Calculate KPIs
    const kpis = calculateKPIs(results)

    // Generate report
    const report = generateReport(results, kpis)

    logger.info(`Simulation completed. Average delay: ${kpis.averageDelay} minutes`)

    res.json({
      success: true,
      scenario_name: scenario.name,
      simulation_time_minutes: duration_minutes,
      kpis,
      results: results.summary,
      report_url: report.url,
    })
  } catch (error) {
    logger.error(`Simulation failed: ${error.message}`)
    res.status(500).json({
      success: false,
      error: error.message,
    })
  }
})

app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  })
})

// KPI calculation function
function calculateKPIs(results) {
  const delays = results.trainEvents.filter((event) => event.type === "delay").map((event) => event.delay_minutes)

  const totalTrains = new Set(results.trainEvents.map((e) => e.train_id)).size
  const onTimeTrains = results.trainEvents.filter(
    (event) => event.type === "arrival" && event.delay_minutes <= 5,
  ).length

  return {
    averageDelay: delays.length > 0 ? delays.reduce((a, b) => a + b, 0) / delays.length : 0,
    maxDelay: delays.length > 0 ? Math.max(...delays) : 0,
    totalDelayMinutes: delays.reduce((a, b) => a + b, 0),
    onTimePerformance: totalTrains > 0 ? (onTimeTrains / totalTrains) * 100 : 100,
    throughput: results.completedJourneys || 0,
    conflictsDetected: results.conflicts?.length || 0,
    delayDistribution: {
      "0-5min": delays.filter((d) => d <= 5).length,
      "5-15min": delays.filter((d) => d > 5 && d <= 15).length,
      "15-30min": delays.filter((d) => d > 15 && d <= 30).length,
      "30+min": delays.filter((d) => d > 30).length,
    },
  }
}

app.listen(port, () => {
  logger.info(`Simulation service running on port ${port}`)
})

module.exports = app
