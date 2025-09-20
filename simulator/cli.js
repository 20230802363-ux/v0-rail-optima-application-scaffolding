#!/usr/bin/env node

const { Command } = require("commander")
const fs = require("fs")
const path = require("path")
const csv = require("csv-parser")
const { SimulationEngine } = require("./src/simulation-engine")
const { generateReport, exportToCSV } = require("./src/report-generator")
const winston = require("winston")

// Configure CLI logging
const logger = winston.createLogger({
  level: "info",
  format: winston.format.combine(winston.format.timestamp(), winston.format.simple()),
  transports: [new winston.transports.Console()],
})

const program = new Command()

program.name("railoptima-simulator").description("Railway operations simulator for scenario analysis").version("1.0.0")

program
  .command("simulate")
  .description("Run a simulation scenario")
  .requiredOption("-t, --timetable <file>", "Timetable CSV file")
  .option("-i, --incidents <file>", "Incidents JSON file")
  .option("-s, --scenario <name>", "Scenario name", "Default Scenario")
  .option("-d, --duration <minutes>", "Simulation duration in minutes", "240")
  .option("-o, --output <file>", "Output report file", "simulation_report.json")
  .option("--csv", "Export results to CSV format")
  .option("--step <seconds>", "Time step in seconds", "60")
  .action(async (options) => {
    try {
      logger.info(`Starting simulation: ${options.scenario}`)

      // Load timetable
      const timetable = await loadTimetableFromCSV(options.timetable)
      logger.info(`Loaded ${timetable.entries.length} timetable entries`)

      // Load incidents (optional)
      let incidents = []
      if (options.incidents) {
        incidents = JSON.parse(fs.readFileSync(options.incidents, "utf8"))
        logger.info(`Loaded ${incidents.length} incidents`)
      }

      // Create simulation engine
      const engine = new SimulationEngine()

      // Run simulation
      const results = await engine.runSimulation({
        scenario: { name: options.scenario },
        timetable,
        incidents,
        duration_minutes: Number.parseInt(options.duration),
        time_step_seconds: Number.parseInt(options.step),
      })

      // Generate report
      const report = generateReport(results, calculateKPIs(results))

      // Save results
      fs.writeFileSync(options.output, JSON.stringify(report, null, 2))
      logger.info(`Report saved to ${options.output}`)

      // Export to CSV if requested
      if (options.csv) {
        const csvFile = options.output.replace(".json", ".csv")
        await exportToCSV(results, csvFile)
        logger.info(`CSV export saved to ${csvFile}`)
      }

      // Print summary
      console.log("\n=== Simulation Summary ===")
      console.log(`Scenario: ${options.scenario}`)
      console.log(`Duration: ${options.duration} minutes`)
      console.log(`Total Events: ${results.trainEvents.length}`)
      console.log(`Conflicts Detected: ${results.conflicts.length}`)
      console.log(`Average Delay: ${report.kpis.averageDelay.toFixed(1)} minutes`)
      console.log(`On-Time Performance: ${report.kpis.onTimePerformance.toFixed(1)}%`)
    } catch (error) {
      logger.error(`Simulation failed: ${error.message}`)
      process.exit(1)
    }
  })

program
  .command("analyze")
  .description("Analyze simulation results")
  .requiredOption("-f, --file <file>", "Simulation results JSON file")
  .option("-c, --compare <file>", "Compare with another simulation file")
  .action(async (options) => {
    try {
      const results = JSON.parse(fs.readFileSync(options.file, "utf8"))

      console.log("\n=== Analysis Results ===")
      console.log(`Total Train Events: ${results.trainEvents.length}`)
      console.log(`Conflicts: ${results.conflicts.length}`)

      // Delay analysis
      const delays = results.trainEvents
        .filter((e) => e.type === "delay")
        .map((e) => e.delay_minutes)
        .sort((a, b) => a - b)

      if (delays.length > 0) {
        console.log(`\nDelay Statistics:`)
        console.log(`  Min: ${Math.min(...delays)} minutes`)
        console.log(`  Max: ${Math.max(...delays)} minutes`)
        console.log(`  Median: ${delays[Math.floor(delays.length / 2)]} minutes`)
        console.log(`  95th percentile: ${delays[Math.floor(delays.length * 0.95)]} minutes`)
      }

      // Compare with another file if provided
      if (options.compare) {
        const compareResults = JSON.parse(fs.readFileSync(options.compare, "utf8"))
        console.log("\n=== Comparison ===")
        console.log(`Events: ${results.trainEvents.length} vs ${compareResults.trainEvents.length}`)
        console.log(`Conflicts: ${results.conflicts.length} vs ${compareResults.conflicts.length}`)
      }
    } catch (error) {
      logger.error(`Analysis failed: ${error.message}`)
      process.exit(1)
    }
  })

program
  .command("generate-scenario")
  .description("Generate a test scenario")
  .requiredOption("-o, --output <file>", "Output scenario file")
  .option("-t, --trains <number>", "Number of trains", "10")
  .option("-d, --duration <hours>", "Scenario duration in hours", "4")
  .action(async (options) => {
    try {
      const scenario = generateTestScenario(Number.parseInt(options.trains), Number.parseInt(options.duration))
      fs.writeFileSync(options.output, JSON.stringify(scenario, null, 2))
      logger.info(`Test scenario generated: ${options.output}`)
    } catch (error) {
      logger.error(`Scenario generation failed: ${error.message}`)
      process.exit(1)
    }
  })

// Helper functions

async function loadTimetableFromCSV(filename) {
  return new Promise((resolve, reject) => {
    const entries = []

    fs.createReadStream(filename)
      .pipe(csv())
      .on("data", (row) => {
        entries.push({
          train_id: row.train_id || row.train_number,
          origin_station: row.origin_station || row.from,
          destination_station: row.destination_station || row.to,
          scheduled_departure: row.scheduled_departure || row.departure_time,
          scheduled_arrival: row.scheduled_arrival || row.arrival_time,
          route: row.route ? row.route.split(",") : [row.origin_station, row.destination_station],
          priority: Number.parseInt(row.priority) || 3,
        })
      })
      .on("end", () => {
        resolve({ entries })
      })
      .on("error", reject)
  })
}

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
  }
}

function generateTestScenario(numTrains, durationHours) {
  const scenario = {
    name: `Test Scenario - ${numTrains} trains, ${durationHours}h`,
    description: "Auto-generated test scenario",
    timetable: { entries: [] },
    incidents: [],
  }

  const stations = ["NDLS", "GZB", "MB", "BE", "LKO", "CNB"]
  const trainTypes = ["express", "passenger", "freight"]

  // Generate trains
  for (let i = 1; i <= numTrains; i++) {
    const trainId = `T${i.toString().padStart(4, "0")}`
    const trainType = trainTypes[Math.floor(Math.random() * trainTypes.length)]
    const origin = stations[Math.floor(Math.random() * stations.length)]
    let destination = stations[Math.floor(Math.random() * stations.length)]

    // Ensure different origin and destination
    while (destination === origin) {
      destination = stations[Math.floor(Math.random() * stations.length)]
    }

    const departureTime = new Date()
    departureTime.setHours(6 + Math.floor(Math.random() * 12)) // 6 AM to 6 PM
    departureTime.setMinutes(Math.floor(Math.random() * 60))

    const arrivalTime = new Date(departureTime)
    arrivalTime.setHours(arrivalTime.getHours() + 2 + Math.floor(Math.random() * 6)) // 2-8 hour journey

    scenario.timetable.entries.push({
      train_id: trainId,
      train_type: trainType,
      origin_station: origin,
      destination_station: destination,
      scheduled_departure: departureTime.toISOString(),
      scheduled_arrival: arrivalTime.toISOString(),
      route: [origin, destination], // Simplified route
      priority: Math.floor(Math.random() * 5) + 1,
    })
  }

  // Generate some random incidents
  const incidentTypes = ["signal_failure", "track_maintenance", "weather", "equipment_failure"]
  const numIncidents = Math.floor(numTrains * 0.1) // 10% of trains affected

  for (let i = 0; i < numIncidents; i++) {
    const incidentType = incidentTypes[Math.floor(Math.random() * incidentTypes.length)]
    const location = stations[Math.floor(Math.random() * stations.length)]

    const startTime = new Date()
    startTime.setHours(8 + Math.floor(Math.random() * 8)) // 8 AM to 4 PM
    startTime.setMinutes(Math.floor(Math.random() * 60))

    const endTime = new Date(startTime)
    endTime.setMinutes(endTime.getMinutes() + 30 + Math.floor(Math.random() * 90)) // 30-120 min duration

    scenario.incidents.push({
      id: `INC${i + 1}`,
      type: incidentType,
      location,
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
      severity: Math.floor(Math.random() * 5) + 1,
      delay_minutes: 10 + Math.floor(Math.random() * 30),
      description: `${incidentType.replace("_", " ")} at ${location}`,
    })
  }

  return scenario
}

// Run CLI
if (require.main === module) {
  program.parse()
}

module.exports = { loadTimetableFromCSV, calculateKPIs, generateTestScenario }
