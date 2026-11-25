// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module logic_analyzer_4ch (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       arm,
    input  wire [3:0] channels,
    input  wire       trigger_falling,
    input  wire [3:0] rd_addr,
    output wire [3:0] rd_data,
    output wire       done,
    output wire       ready_to_trigger
);
    localparam [1:0] IDLE         = 2'b00,
                     WAIT_TRIGGER = 2'b01,
                     CAPTURE      = 2'b10,
                     READY        = 2'b11;

    reg [1:0] state;
    reg       prev_arm;
    reg       prev_ch0;
    reg       falling;
    reg [3:0] wr_addr;
    reg [3:0] start_addr;
    reg [3:0] history_count;
    reg [2:0] post_remaining;
    reg [3:0] samples [0:15];

    wire arm_rise = arm & ~prev_arm;
    wire ch0_edge = (channels[0] != prev_ch0) & (channels[0] ^ falling);
    wire trigger = ready_to_trigger & ch0_edge;
    wire [3:0] physical_rd_addr = start_addr + rd_addr;

    always @(posedge clk) begin
        if (!rst_n) begin
            state          <= IDLE;
            prev_arm       <= 1'b0;
            prev_ch0       <= 1'b0;
            falling        <= 1'b0;
            wr_addr        <= 4'd0;
            start_addr     <= 4'd0;
            history_count  <= 4'd0;
            post_remaining <= 3'd0;
        end else begin
            prev_arm <= arm;
            prev_ch0 <= channels[0];

            // Before the trigger, each write replaces the oldest sample.
            if (state == WAIT_TRIGGER || state == CAPTURE) begin
                samples[wr_addr] <= channels;
                wr_addr <= wr_addr + 4'd1;
            end

            case (state)
                IDLE, READY: begin
                    if (arm_rise) begin
                        wr_addr       <= 4'd0;
                        history_count <= 4'd0;
                        falling       <= trigger_falling;
                        state         <= WAIT_TRIGGER;
                    end
                end

                WAIT_TRIGGER: begin
                    if (trigger) begin
                        // The current write is sample 8 in the final window.
                        start_addr     <= wr_addr - 4'd8;
                        post_remaining <= 3'd7;
                        state          <= CAPTURE;
                    end else if (!ready_to_trigger) begin
                        history_count <= history_count + 4'd1;
                    end
                end

                CAPTURE: begin
                    if (post_remaining == 3'd1)
                        state <= READY;
                    else
                        post_remaining <= post_remaining - 3'd1;
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign ready_to_trigger = (state == WAIT_TRIGGER) && (history_count == 4'd8);
    assign done = (state == READY);
    // Read one word from each bank, then select the bank by its upper bits.
    wire [15:0] bank_words;
    genvar bank;
    generate
        for (bank = 0; bank < 4; bank = bank + 1) begin : read_bank
            localparam [1:0] BANK_ID = bank;
            assign bank_words[bank*4 +: 4] =
                samples[{BANK_ID, physical_rd_addr[1:0]}];
        end
    endgenerate
    assign rd_data = done ? bank_words[{physical_rd_addr[3:2], 2'b00} +: 4] : 4'b0;
endmodule

`default_nettype wire
