// Small UUID generator with fallback for environments missing crypto.randomUUID
export function generateId(): string {
  try {
    if (typeof crypto !== 'undefined') {
      // Preferred: platform-provided secure UUID
      if (typeof (crypto as any).randomUUID === 'function') {
        return (crypto as any).randomUUID();
      }
      // Fallback: RFC4122 v4 using getRandomValues
      if (typeof (crypto as any).getRandomValues === 'function') {
        // https://stackoverflow.com/a/2117523/119527
        return ([1e7] as any + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c: any) => (
          (c ^ ((crypto as any).getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4))))
          .toString(16)
        ));
      }
    }
  } catch {
    // fallthrough
  }
  // Last-resort (not cryptographically secure)
  return 'id-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}
