/**
 * The host of a video: dispatches on the project's avatar.
 *
 *  builtin toon-*  -> parametric cartoon (Presenter)
 *  builtin real-*  -> semi-realistic illustration (RealPresenter)
 *  photo           -> the user's uploaded picture (PhotoPresenter)
 *
 * Takes exactly the Presenter's props plus `avatar` (the project's avatar payload). Unknown
 * built-in ids fall back to the original cartoon host.
 */
import React from 'react';
import { avatarSpec } from '../avatars';
import type { AvatarPayload } from '../schema';
import type { HostProps } from './hostMotion';
import { PhotoPresenter } from './PhotoPresenter';
import { Presenter } from './Presenter';
import { RealPresenter } from './RealPresenter';

export type HostComponentProps = HostProps & { avatar?: AvatarPayload | null };

export const Host: React.FC<HostComponentProps> = ({ avatar, ...rest }) => {
  if (avatar?.kind === 'photo') {
    return <PhotoPresenter {...rest} imageUrl={avatar.imageUrl} mode={avatar.mode} />;
  }
  const spec = avatarSpec(avatar?.id);
  if (spec.style === 'real') return <RealPresenter {...rest} spec={spec} />;
  return <Presenter {...rest} look={spec.look} />;
};
