/** Counters and switches the e2e specs install in the page before it loads. */
interface Window {
  __runPosts?: number;
  __runBodies?: string[];
  __fixtureRunFailure?: { code: string; message: string };
  __fixtureRunStreamCut?: number;
}
