import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

const RESIZE_OBSERVER_LOOP_MESSAGE = 'ResizeObserver loop completed with undelivered notifications.';

window.addEventListener(
  'error',
  (event) => {
    const hasResizeObserverLoopMessage =
      event.message?.includes(RESIZE_OBSERVER_LOOP_MESSAGE) ||
      (event.error instanceof Error && event.error.cause instanceof Error && event.error.cause.message.includes(RESIZE_OBSERVER_LOOP_MESSAGE));

    if (!hasResizeObserverLoopMessage) {
      return;
    }

    // This browser warning is non-fatal but Angular global listeners can surface it as an error.
    event.preventDefault();
    event.stopImmediatePropagation();
  },
  true
);

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
