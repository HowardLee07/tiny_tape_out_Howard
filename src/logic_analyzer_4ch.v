// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module logic_analyzer_4ch (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       arm,
    input  wire [3:0] channels,
    input  wire [3:0] trigger_mask,
    input  wire [3:0] trigger_value,
    input  wire [4:0] rd_addr,
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
    reg       prev_match;
    reg [3:0] mask;
    reg [3:0] value;
    reg [4:0] wr_addr;
    reg [4:0] start_addr;
    reg [4:0] history_count;
    reg [3:0] post_remaining;
    reg [3:0] samples [0:31];

    wire arm_rise = arm & ~prev_arm;
    wire pattern_match = ((channels ^ value) & mask) == 4'd0;
    wire trigger = ready_to_trigger & pattern_match & ~prev_match;
    wire [4:0] physical_rd_addr = start_addr + rd_addr;

    always @(posedge clk) begin
        if (!rst_n) begin
            state          <= IDLE;
            prev_arm       <= 1'b0;
            prev_match     <= 1'b0;
            mask           <= 4'd0;
            value          <= 4'd0;
            wr_addr        <= 5'd0;
            start_addr     <= 5'd0;
            history_count  <= 5'd0;
            post_remaining <= 4'd0;
        end else begin
            prev_arm <= arm;
            prev_match <= pattern_match;

            // Before the trigger, each write replaces the oldest sample.
            if (state == WAIT_TRIGGER || state == CAPTURE) begin
                samples[wr_addr] <= channels;
                wr_addr <= wr_addr + 5'd1;
            end

            case (state)
                IDLE, READY: begin
                    if (arm_rise) begin
                        wr_addr       <= 5'd0;
                        history_count <= 5'd0;
                        mask          <= trigger_mask;
                        value         <= trigger_value;
                        state         <= WAIT_TRIGGER;
                    end
                end

                WAIT_TRIGGER: begin
                    if (trigger) begin
                        // The current write is sample 16 in the final window.
                        start_addr     <= wr_addr - 5'd16;
                        post_remaining <= 4'd15;
                        state          <= CAPTURE;
                    end else if (!ready_to_trigger) begin
                        history_count <= history_count + 5'd1;
                    end
                end

                CAPTURE: begin
                    if (post_remaining == 4'd1)
                        state <= READY;
                    else
                        post_remaining <= post_remaining - 4'd1;
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign ready_to_trigger = (state == WAIT_TRIGGER) && (history_count == 5'd16);
    assign done = (state == READY);
    assign rd_data = done ? samples[physical_rd_addr] : 4'b0;
endmodule

`default_nettype wire
