import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import useSpeechGateway from "./use-speech-gateway";

// Mock React
vi.mock("react", () => {
  let stateVal = "Offline";
  const stateSetter = vi.fn((val) => {
    stateVal = val;
  });
  return {
    useState: vi.fn((initial) => [stateVal, stateSetter]),
    useEffect: vi.fn((effect, deps) => {
      // Simulate mounting/unmounting
      const cleanup = effect();
      return cleanup;
    }),
    useRef: vi.fn((initial) => ({ current: initial })),
    useCallback: vi.fn((fn) => fn),
  };
});

// Mock dependencies
vi.mock("@/app/lib/websocket/reconnect-backoff", () => ({
  getReconnectDelayMs: vi.fn(() => 10),
}));

vi.mock("../auth/ws-ticket", () => ({
  fetchWsTicket: vi.fn(async () => "mock_ticket"),
}));

describe("useSpeechGateway", () => {
  let originalWebSocket;
  let originalNavigator;
  let originalMediaRecorder;

  beforeEach(() => {
    originalWebSocket = global.WebSocket;
    originalNavigator = global.navigator;
    originalMediaRecorder = global.MediaRecorder;

    // Set mock env
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";

    // Mock window.addEventListener/removeEventListener for beforeunload
    if (typeof window === "undefined") {
      global.window = {};
    }
    global.window.addEventListener = vi.fn();
    global.window.removeEventListener = vi.fn();
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    global.navigator = originalNavigator;
    global.MediaRecorder = originalMediaRecorder;
    vi.restoreAllMocks();
  });

  it("should initialize state and manage websocket lifecycle", async () => {
    const mockWs = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: 1, // WebSocket.OPEN
    };
    global.WebSocket = vi.fn().mockImplementation(function() {
      return mockWs;
    });

    const mockTrack = { stop: vi.fn() };
    const mockStream = {
      getTracks: vi.fn(() => [mockTrack]),
    };

    Object.defineProperty(global, "navigator", {
      value: {
        mediaDevices: {
          getUserMedia: vi.fn(async () => mockStream),
        },
      },
      writable: true,
      configurable: true,
    });

    const mockRecorder = {
      start: vi.fn(),
      stop: vi.fn(),
      state: "recording",
    };
    global.MediaRecorder = vi.fn().mockImplementation(function() {
      return mockRecorder;
    });
    global.MediaRecorder.isTypeSupported = vi.fn(() => true);

    // Call hook
    const { gatewayStatus } = useSpeechGateway("meeting_123", "jwt_abc", true);

    // Wait for ticket fetch and websocket instantiation async microtasks
    await new Promise((resolve) => setTimeout(resolve, 5));

    // Simulate WebSocket open event to trigger capture
    mockWs.onopen();

    // Wait for async getUserMedia to resolve and initialize MediaRecorder
    await new Promise((resolve) => setTimeout(resolve, 5));

    // Verify connections and recorders were initialized
    expect(global.WebSocket).toHaveBeenCalled();
    expect(global.navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
    expect(global.MediaRecorder).toHaveBeenCalled();
    expect(mockRecorder.start).toHaveBeenCalledWith(250);
  });

  it("should handle error failover and trigger reconnect", async () => {
    // Force WS connection to fail or close
    const mockWs = {
      close: vi.fn(),
    };
    global.WebSocket = vi.fn().mockImplementation(function() {
      return mockWs;
    });

    useSpeechGateway("meeting_123", "jwt_abc", true);

    // Wait for ticket fetch and websocket instantiation async microtasks
    await new Promise((resolve) => setTimeout(resolve, 5));

    // Trigger close handler to simulate disconnect
    expect(mockWs.onclose).toBeDefined();
    mockWs.onclose();
  });
});
