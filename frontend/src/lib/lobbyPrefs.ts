const PERSONALITY_KEY = 'werewolf.personalityLibId'
const STRATEGY_KEY = 'werewolf.strategyLibId'

export function loadLobbyLibraryPrefs(): { personalityLibId: string; strategyLibId: string } {
  return {
    personalityLibId: localStorage.getItem(PERSONALITY_KEY) ?? 'default',
    strategyLibId: localStorage.getItem(STRATEGY_KEY) ?? 'default',
  }
}

export function saveLobbyLibraryPrefs(prefs: {
  personalityLibId?: string
  strategyLibId?: string
}): void {
  if (prefs.personalityLibId != null) {
    localStorage.setItem(PERSONALITY_KEY, prefs.personalityLibId)
  }
  if (prefs.strategyLibId != null) {
    localStorage.setItem(STRATEGY_KEY, prefs.strategyLibId)
  }
}
