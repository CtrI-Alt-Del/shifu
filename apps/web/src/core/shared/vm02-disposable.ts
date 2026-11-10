// Disposable code for the SHIFU-87 VM-02 check. It is never merged.
export function vm02Clamp(value: number, min: number, max: number): number {
  if (value < min) {
    return min
  }
  if (value > max) {
    return max
  }
  return value
}

export function vm02Sign(value: number): number {
  if (value > 0) {
    return 1
  }
  if (value < 0) {
    return -1
  }
  return 0
}

export function vm02Label(value: number): string {
  if (value < 10) {
    return 'low'
  }
  if (value < 100) {
    return 'medium'
  }
  return 'high'
}

export function vm02Grade(score: number): string {
  if (score >= 90) {
    return 'A'
  }
  if (score >= 80) {
    return 'B'
  }
  if (score >= 70) {
    return 'C'
  }
  return 'D'
}

export function vm02Bucket(value: number): number {
  if (value < 0) {
    return 0
  }
  if (value < 50) {
    return 1
  }
  if (value < 500) {
    return 2
  }
  return 3
}

export function vm02Parity(value: number): string {
  if (value % 2 === 0) {
    return 'even'
  }
  return 'odd'
}
