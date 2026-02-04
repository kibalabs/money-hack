import React from 'react';

import { Alignment, Box, Direction, Stack } from '@kibalabs/ui-react';

import './StepProgress.scss';

export interface IStepProgressProps {
  currentStep: number;
  totalSteps: number;
}

export function StepProgress(props: IStepProgressProps): React.ReactElement {
  return (
    <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullWidth={true}>
      {Array.from({ length: props.totalSteps }, (_, index: number): React.ReactElement => (
        <Stack.Item key={index} growthFactor={1} shrinkFactor={1}>
          <Box className={`stepIndicator ${index < props.currentStep ? 'active' : ''}`} />
        </Stack.Item>
      ))}
    </Stack>
  );
}
