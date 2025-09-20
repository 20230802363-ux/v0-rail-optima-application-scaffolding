const { SimulationEngine, Train, Track } = require("../src/simulation-engine")
const { generateReport } = require("../src/report-generator")

describe("SimulationEngine", () => {
  let engine

  beforeEach(() => {
    engine = new SimulationEngine()
  })

  test("should initialize correctly", () => {
    expect(engine.trains.size).toBe(0)
    expect(engine.tracks.size).toBe(0)
    expect(engine.currentTime).toBe(0)
    expect(engine.isRunning).toBe(false)
  })

  test("should initialize from timetable", () => {
    const timetable = {
      entries: [
        {
          train_id: "T001",
          train_type: "express",
          route: ["NDLS", "GZB", "LKO"],
          scheduled_departure: new Date().toISOString(),
          scheduled_arrival: new Date(Date.now() + 3600000).toISOString(),
          priority: 1,
        },
      ],
    }

    engine.initializeFromTimetable(timetable)

    expect(engine.trains.size).toBe(1)
    expect(engine.stations.size).toBe(3)

    const train = engine.trains.get("T001")
    expect(train.type).toBe("express")
    expect(train.route).toEqual(["NDLS", "GZB", "LKO"])
  })

  test("should run simulation", async () => {
    const scenario = { name: "Test Scenario" }
    const timetable = {
      entries: [
        {
          train_id: "T001",
          train_type: "passenger",
          route: ["A", "B"],
          scheduled_departure: new Date().toISOString(),
          scheduled_arrival: new Date(Date.now() + 1800000).toISOString(),
          priority: 2,
        },
      ],
    }

    const results = await engine.runSimulation({
      scenario,
      timetable,
      incidents: [],
      duration_minutes: 60,
      time_step_seconds: 60,
    })

    expect(results).toBeDefined()
    expect(results.scenario).toBe("Test Scenario")
    expect(results.trainEvents).toBeDefined()
    expect(results.summary).toBeDefined()
    expect(results.completedJourneys).toBeGreaterThanOrEqual(0)
  })

  test("should handle incidents", () => {
    const incident = {
      id: "INC001",
      type: "signal_failure",
      location: "NDLS",
      start_time: new Date().toISOString(),
      end_time: new Date(Date.now() + 1800000).toISOString(),
      delay_minutes: 15,
    }

    engine.initializeIncidents([incident])
    expect(engine.incidents.length).toBe(1)

    const processedIncident = engine.incidents[0]
    expect(processedIncident.active).toBe(false)
    expect(processedIncident.startTime).toBeDefined()
  })

  test("should detect conflicts", () => {
    // Create a track with capacity 1
    const track = new Track({
      segment_id: "A-B",
      from_station: "A",
      to_station: "B",
      capacity: 1,
    })

    // Simulate two trains occupying the same track
    track.occupyTrack("T001")
    track.occupyTrack("T002")

    engine.tracks.set("A-B", track)

    const conflicts = engine.detectConflicts()
    expect(conflicts.length).toBeGreaterThan(0)
    expect(conflicts[0].type).toBe("track_overoccupancy")
  })
})

describe("Train", () => {
  test("should initialize train correctly", () => {
    const trainData = {
      train_id: "T001",
      train_type: "express",
      route: ["NDLS", "GZB", "LKO"],
      scheduled_departure: new Date().toISOString(),
      scheduled_arrival: new Date(Date.now() + 3600000).toISOString(),
      priority: 1,
    }

    const train = new Train(trainData)

    expect(train.id).toBe("T001")
    expect(train.type).toBe("express")
    expect(train.maxSpeed).toBe(130) // Express train max speed
    expect(train.status).toBe("scheduled")
    expect(train.currentStation).toBe("NDLS")
  })

  test("should update position correctly", () => {
    const train = new Train({
      train_id: "T001",
      train_type: "passenger",
      route: ["A", "B"],
      scheduled_departure: new Date().toISOString(),
      scheduled_arrival: new Date(Date.now() + 3600000).toISOString(),
    })

    train.status = "running"
    train.speed = 60 // 60 km/h

    const initialPosition = train.position
    train.updatePosition(3600, 60) // 1 hour, 60km track

    expect(train.position).toBeGreaterThan(initialPosition)
    expect(train.distanceTraveled).toBeGreaterThan(0)
  })

  test("should apply incidents correctly", () => {
    const train = new Train({
      train_id: "T001",
      train_type: "passenger",
      route: ["A", "B"],
      scheduled_departure: new Date().toISOString(),
      scheduled_arrival: new Date(Date.now() + 3600000).toISOString(),
    })

    const incident = {
      id: "INC001",
      type: "signal_failure",
      delay_minutes: 10,
    }

    const originalSpeed = train.speed
    train.applyIncident(incident)

    expect(train.incidents.length).toBe(1)
    expect(train.speed).toBeLessThanOrEqual(20) // Speed restricted due to signal failure
  })
})

describe("Report Generation", () => {
  test("should generate comprehensive report", () => {
    const mockResults = {
      scenario: "Test Scenario",
      trainEvents: [
        {
          type: "departure",
          train_id: "T001",
          delay_minutes: 5,
          timestamp: new Date(),
        },
        {
          type: "arrival",
          train_id: "T001",
          delay_minutes: 8,
          timestamp: new Date(),
        },
      ],
      conflicts: [
        {
          type: "track_conflict",
          trains: ["T001", "T002"],
          severity: "medium",
        },
      ],
      summary: {
        totalTrains: 2,
        completedTrains: 1,
        onTimePerformance: 75,
        averageDelay: 6.5,
      },
      trackUtilization: [],
    }

    const kpis = {
      averageDelay: 6.5,
      onTimePerformance: 75,
      throughput: 1,
      conflictsDetected: 1,
    }

    const report = generateReport(mockResults, kpis)

    expect(report).toBeDefined()
    expect(report.metadata).toBeDefined()
    expect(report.kpis).toBeDefined()
    expect(report.analysis).toBeDefined()
    expect(report.recommendations).toBeDefined()
    expect(report.charts).toBeDefined()

    // Check that recommendations are generated for poor performance
    expect(report.recommendations.length).toBeGreaterThan(0)
  })
})
