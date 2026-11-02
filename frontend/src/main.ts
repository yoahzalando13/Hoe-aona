import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { appConfig } from './app/app.config';
import { LANG } from './app/core/i18n';

document.documentElement.lang = LANG;

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
