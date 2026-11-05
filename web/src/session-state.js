// Async results are valid only for the identity generation that started them.
// Returning to the same user after logout is a new generation, not a valid old read.
export function createIdentityScope() {
  let userId = null;
  let generation = 0;
  return {
    setUser(next) {
      if (next === userId) return false;
      userId = next;
      generation += 1;
      return true;
    },
    ticket() { return { userId, generation }; },
    accepts(ticket) { return ticket.userId === userId && ticket.generation === generation; },
  };
}
