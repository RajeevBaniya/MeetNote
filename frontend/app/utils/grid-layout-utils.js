/**
 * Grid Layout Utility Functions
 * 
 * Centralized logic for determining grid layouts based on participant count.
 * This ensures consistent layout behavior across the application.
 */

import { GRID_LAYOUT_BREAKPOINTS } from "@/app/constants/meeting-constants";

/**
 * Determines the appropriate grid class based on participant count
 * 
 * @param {number} participantCount - Number of participants
 * @param {boolean} isCompact - Whether in compact mode (screen sharing)
 * @returns {string} - Tailwind CSS grid class
 */
export function getGridLayoutClass(participantCount, isCompact = false) {
  if (isCompact) {
    return "grid-cols-1";
  }

  if (participantCount === GRID_LAYOUT_BREAKPOINTS.SINGLE) {
    return "grid-cols-1";
  }

  if (participantCount === GRID_LAYOUT_BREAKPOINTS.TWO) {
    return "grid-cols-1 sm:grid-cols-2";
  }

  if (participantCount <= GRID_LAYOUT_BREAKPOINTS.FOUR) {
    return "grid-cols-2";
  }

  if (participantCount <= GRID_LAYOUT_BREAKPOINTS.SIX) {
    return "grid-cols-2 md:grid-cols-3";
  }

  if (participantCount <= GRID_LAYOUT_BREAKPOINTS.NINE) {
    return "grid-cols-2 md:grid-cols-3";
  }

  if (participantCount <= GRID_LAYOUT_BREAKPOINTS.TWELVE) {
    return "grid-cols-2 md:grid-cols-3 lg:grid-cols-4";
  }

  if (participantCount <= GRID_LAYOUT_BREAKPOINTS.SIXTEEN) {
    return "grid-cols-3 md:grid-cols-4";
  }

  return "grid-cols-3 md:grid-cols-4 lg:grid-cols-5";
}