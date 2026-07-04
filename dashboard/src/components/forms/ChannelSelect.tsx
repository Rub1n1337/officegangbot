import { BsChatLeftText as ChatIcon } from 'react-icons/bs';
import { GuildChannel } from '@/api/bot';
import { ChannelTypes } from '@/api/discord';
import { Option, SelectField } from '@/components/forms/SelectField';
import { forwardRef, useMemo } from 'react';
import { MdRecordVoiceOver } from 'react-icons/md';
import { useGuildChannelsQuery } from '@/api/hooks';
import { Icon } from '@chakra-ui/react';
import { useRouter } from 'next/router';
import { SelectInstance, Props as SelectProps } from 'chakra-react-select';
import { Override } from '@/utils/types';
import { ControlledInput } from './types';
import { FormCard, FormCardProps } from './Form';
import { useController, UseControllerProps } from 'react-hook-form';
import { common } from '@/config/translations/common';

/**
 * Render an options
 */
const render = (channel: GuildChannel): Option => {
  const icon = () => {
    switch (channel.type) {
      case ChannelTypes.GUILD_STAGE_VOICE:
      case ChannelTypes.GUILD_VOICE: {
        return <Icon as={MdRecordVoiceOver} />;
      }
      default:
        return <ChatIcon />;
    }
  };

  return {
    label: channel.name,
    value: channel.id,
    icon: icon(),
  };
};

function mapOptions(channels: GuildChannel[]) {
  //channels in category
  const categories = new Map<string, GuildChannel[]>();
  //channels with no parent category
  const roots: GuildChannel[] = [];

  //group channels
  for (const channel of channels) {
    if (channel.category == null) roots.push(channel);
    else {
      const category = categories.get(channel.category);

      if (category == null) {
        categories.set(channel.category, [channel]);
      } else {
        category.push(channel);
      }
    }
  }

  //map channels into select menu options
  return roots.map((channel) => {
    if (channel.type === ChannelTypes.GUILD_CATEGORY) {
      return {
        ...render(channel),
        options: categories.get(channel.id)?.map(render) ?? [],
      };
    }

    return render(channel);
  });
}

type Props = Override<
  SelectProps<Option, false>,
  {
    value?: string;
    onChange: (v: string | null) => void;
  }
>;

export const ChannelSelect = forwardRef<SelectInstance<Option, false>, Props>(
  ({ value, onChange, ...rest }, ref) => {
    const guild = useRouter().query.guild as string;
    const channelsQuery = useGuildChannelsQuery(guild);
    const isLoading = channelsQuery.isLoading;

    const selected = value != null ? channelsQuery.data?.find((c) => c.id === value) : null;
    const options = useMemo(
      () => (channelsQuery.data != null ? mapOptions(channelsQuery.data) : []),
      [channelsQuery.data]
    );

    return (
      <SelectField<Option>
        isDisabled={isLoading}
        isLoading={isLoading}
        isClearable
        placeholder={<common.T text="select channel" />}
        value={selected != null ? render(selected) : null}
        options={options}
        // Pass null on clear so an optional channel can actually be unset (the
        // form sends null and the bot clears the column).
        onChange={(e) => onChange(e?.value ?? null)}
        ref={ref}
        {...rest}
      />
    );
  }
);

ChannelSelect.displayName = 'ChannelSelect';

export const ChannelSelectForm: ControlledInput<Omit<Props, 'value' | 'onChange'>> = ({
  control,
  controller,
  ...props
}) => {
  const { field, fieldState } = useController(controller);

  return (
    <FormCard {...control} error={fieldState.error?.message}>
      <ChannelSelect {...field} {...props} />
    </FormCard>
  );
};

// Multi-select variant: the field value is a string[] of channel ids.
type MultiFormProps = {
  control: Omit<FormCardProps, 'error' | 'children'>;
  controller: UseControllerProps<any>;
};

export const ChannelMultiSelectForm = ({ control, controller }: MultiFormProps) => {
  const { field, fieldState } = useController(controller);
  const guild = useRouter().query.guild as string;
  const channelsQuery = useGuildChannelsQuery(guild);
  const value: string[] = field.value ?? [];
  const options = useMemo(
    () => (channelsQuery.data != null ? mapOptions(channelsQuery.data) : []),
    [channelsQuery.data]
  );
  const selected = value
    .map((id) => channelsQuery.data?.find((c) => c.id === id))
    .filter((c): c is GuildChannel => c != null)
    .map(render);

  return (
    <FormCard {...control} error={fieldState.error?.message}>
      <SelectField
        isMulti
        isDisabled={channelsQuery.isLoading}
        isLoading={channelsQuery.isLoading}
        placeholder={<common.T text="select channel" />}
        value={selected}
        onChange={(vals: any) => field.onChange(((vals ?? []) as Option[]).map((v) => v.value))}
        options={options}
      />
    </FormCard>
  );
};
