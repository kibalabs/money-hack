import React from 'react';

import './LoadingIndicator.scss';

export function LoadingIndicator(): React.ReactElement {
  return (
    <div className='loadingIndicator' aria-label='Loading'>
      <div className='loadingIndicatorDot' />
      <div className='loadingIndicatorDot' />
      <div className='loadingIndicatorDot' />
    </div>
  );
}
