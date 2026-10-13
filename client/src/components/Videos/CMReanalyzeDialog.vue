<template>
    <v-dialog max-width="560" :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">もう一度 CM 解析しますか？</v-card-title>
            <v-card-text class="pt-2 pb-0">
                <div v-if="total === 1">
                    この録画番組は、すでに現在と同じバージョンの AI ({{label}}) で CM 解析済みです。
                </div>
                <div v-else>
                    選択した {{total}} 件のうち {{count}} 件は、すでに現在と同じバージョンの AI ({{label}}) で CM 解析済みです。
                </div>
                <div class="mt-2 text-text-darken-1">
                    再解析しても結果はほとんど変わりません。再解析には 1 件あたり数分かかります。
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" @click="emit('update:modelValue', false)">
                    <span>キャンセル</span>
                </v-btn>
                <v-btn class="px-3" color="primary" variant="flat" @click="confirm">
                    <span>再解析する</span>
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>
<script lang="ts" setup>

defineProps<{
    modelValue: boolean;
    count: number;
    total: number;
    label: string;
}>();

const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void;
    (e: 'confirm'): void;
}>();

const confirm = () => {
    emit('update:modelValue', false);
    emit('confirm');
};

</script>
