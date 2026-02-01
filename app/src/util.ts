import React from 'react';

import { isBrowser } from '@kibalabs/core';


export const getIsNextVersion = (): boolean => {
  if (isBrowser() && window.KRT_IS_NEXT && window.KRT_IS_NEXT != null && ['1', 'true', 'yes', 'y', 'on'].includes(window.KRT_IS_NEXT.toLowerCase())) {
    return true;
  }
  return false;
};

export const usePrefersDarkMode = (): boolean => {
  const [prefersDarkMode, setPrefersDarkMode] = React.useState<boolean>(
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : false,
  );
  React.useEffect((): (() => void) | void => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent): void => setPrefersDarkMode(e.matches);
    mediaQuery.addEventListener('change', handleChange);
    return (): void => mediaQuery.removeEventListener('change', handleChange);
  }, []);
  return prefersDarkMode;
};
