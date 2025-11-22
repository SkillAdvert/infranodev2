/**
 * MSW Server Configuration
 *
 * Sets up the Mock Service Worker server for intercepting
 * HTTP requests during tests.
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Create the server with default handlers
export const server = setupServer(...handlers);

// Export for use in tests that need custom handlers
export { handlers };
