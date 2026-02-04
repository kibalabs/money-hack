import React from 'react';

import { getClassName } from '@kibalabs/core';
import { ISingleAnyChildProps } from '@kibalabs/core-react';
import { Box, Button, IBoxProps, IButtonProps, ITextProps, Text } from '@kibalabs/ui-react';

import './GlowingButton.scss';

export function GlowingButton(props: IButtonProps): React.ReactElement {
  return (
    <div className='GlowingButton' style={{ ...props.style, width: props.isFullWidth ? '100%' : 'auto' }}>
      {/* eslint-disable-next-line react/jsx-props-no-spreading */}
      <Button {...props} />
    </div>
  );
}

export function GlowingText(props: ITextProps): React.ReactElement {
  return (
    <div className={getClassName('GlowingText', props.className)} style={props.style}>
      {/* eslint-disable-next-line react/jsx-props-no-spreading */}
      <Text {...props} className='GlowingTextColored' />
    </div>
  );
}

export const glowingBannerClassName = 'GlowingBanner';

export function GlowingBorderBox(props: IBoxProps & ISingleAnyChildProps): React.ReactElement {
  return (
    <Box id={props.id} className={getClassName(props.className, 'GlowingBorder')}>
      <Box style={props.style}>
        {props.children}
      </Box>
    </Box>
  );
}
