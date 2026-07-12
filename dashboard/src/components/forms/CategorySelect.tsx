import { GuildChannel } from '@/api/bot';
import { ChannelTypes } from '@/api/discord';
import { Option, SelectField } from '@/components/forms/SelectField';
import { forwardRef, useMemo } from 'react';
import { MdFolder } from 'react-icons/md';
import { useGuildChannelsQuery } from '@/api/hooks';
import { Icon } from '@chakra-ui/react';
import { useRouter } from 'next/router';
import { SelectInstance, Props as SelectProps } from 'chakra-react-select';
import { Override } from '@/utils/types';
import { ControlledInput } from './types';
import { FormCard } from './Form';
import { useController } from 'react-hook-form';
import { useFormText } from '@/config/translations/form-text';

const render = (channel: GuildChannel): Option => ({
  label: channel.name,
  value: channel.id,
  icon: <Icon as={MdFolder} />,
});

type Props = Override<
  SelectProps<Option, false>,
  {
    value?: string;
    onChange: (v: string) => void;
  }
>;

/**
 * Like ChannelSelect, but lists category channels as the selectable options
 * (ChannelSelect uses categories only as group headers).
 */
export const CategorySelect = forwardRef<SelectInstance<Option, false>, Props>(
  ({ value, onChange, ...rest }, ref) => {
    const guild = useRouter().query.guild as string;
    const ft = useFormText();
    const channelsQuery = useGuildChannelsQuery(guild);
    const isLoading = channelsQuery.isLoading;

    const categories = useMemo(
      () => (channelsQuery.data ?? []).filter((c) => c.type === ChannelTypes.GUILD_CATEGORY),
      [channelsQuery.data]
    );
    const selected = value != null ? categories.find((c) => c.id === value) : null;

    return (
      <SelectField<Option>
        isDisabled={isLoading}
        isLoading={isLoading}
        placeholder={ft('Select a category')}
        value={selected != null ? render(selected) : null}
        options={categories.map(render)}
        onChange={(e) => e != null && onChange(e.value)}
        ref={ref}
        {...rest}
      />
    );
  }
);

CategorySelect.displayName = 'CategorySelect';

export const CategorySelectForm: ControlledInput<Omit<Props, 'value' | 'onChange'>> = ({
  control,
  controller,
  ...props
}) => {
  const { field, fieldState } = useController(controller);

  return (
    <FormCard {...control} error={fieldState.error?.message}>
      <CategorySelect {...field} {...props} />
    </FormCard>
  );
};
