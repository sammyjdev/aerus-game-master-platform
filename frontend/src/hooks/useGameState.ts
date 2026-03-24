import { useGameStore } from '../store/gameStore'

export function useGameState() {
  const gameState = useGameStore((state) => state.gameState)
  const applyDelta = useGameStore((state) => state.applyDelta)
  const applyFullSync = useGameStore((state) => state.applyFullSync)
  const appendNarrativeToken = useGameStore((state) => state.appendNarrativeToken)
  const setPendingDiceRoll = useGameStore((state) => state.setPendingDiceRoll)
  const setPendingManualRoll = useGameStore((state) => state.setPendingManualRoll)
  const setManualRollResolution = useGameStore((state) => state.setManualRollResolution)
  const addHistoryEntry = useGameStore((state) => state.addHistoryEntry)
  const handleGameEvent = useGameStore((state) => state.handleGameEvent)

  return {
    gameState,
    applyDelta,
    applyFullSync,
    appendNarrativeToken,
    setPendingDiceRoll,
    setPendingManualRoll,
    setManualRollResolution,
    addHistoryEntry,
    handleGameEvent,
  }
}
