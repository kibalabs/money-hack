import React from 'react';

import { ISingleAnyChildProps } from '@kibalabs/core-react';
import { Box } from '@kibalabs/ui-react';

interface IContainingViewProps extends ISingleAnyChildProps {
  className?: string;
}

export function ContainingView(props: IContainingViewProps): React.ReactElement {
  return (
    <Box className={props.className} variant='blank' isScrollableVertically={true} isFullWidth={true}>{props.children}</Box>
  );
}
